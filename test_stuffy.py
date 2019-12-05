from stuffy import StuffyNode, StuffyObject
from pymongo import MongoClient
from pymongo.cursor import Cursor
from time import sleep
import json

MONGO_URI_DOWDING = "mongodb+srv://hugh_dowding:19dowding40@chainhome-cicbu.mongodb.net/test?retryWrites=true&w=majority"
MONGO_URI_WATT = "mongodb+srv://robert_watt:19dowding40@chainhome-cicbu.mongodb.net/test?retryWrites=true&w=majority"
MONGO_URI_WILKINS = "mongodb+srv://anthony_wilkins:19dowding40@chainhome-cicbu.mongodb.net/test?retryWrites=true&w=majority"
MONGO_ADMIN_URI = "mongodb+srv://air_marshal:19dowding40@chainhome-cicbu.mongodb.net/test?retryWrites=true&w=majority"
DOS_TEST_1 = {"dog": 42, "cat": [1, 2, 3, 4], "mouse": {"cheese": -1}}
DOS_TEST_2 = {"subject": "This is the test!", "message": "I say chaps!"}


def reset_database():
    db = MongoClient(MONGO_ADMIN_URI)['stuffy']
    db.new.delete_many({})
    db.anthony_wilkins.delete_many({})
    db.anthony_wilkins.delete_many({})
    db.robert_watt.delete_many({})
    db.hugh_dowding.delete_many({})

def test_stuffy_object():
    d = DOS_TEST_2
    so = StuffyObject(d)
    assert isinstance(so, StuffyObject)
    assert isinstance(so.dict_of_stuff, dict)
    assert so.dict_of_stuff == DOS_TEST_2
    assert so.channel == 'stuffy'
    assert so.already_read == False
    assert so.delivered == False

    class MyObject(StuffyObject):
        def __init__(self, dict_of_stuff):
            super().__init__(dict_of_stuff)

    assert issubclass(MyObject, StuffyObject)
    so = MyObject(d)
    assert isinstance(so, StuffyObject)
    assert isinstance(so.dict_of_stuff, dict)
    assert so.dict_of_stuff == DOS_TEST_2
    assert so.channel == 'stuffy'
    assert so.already_read == False
    assert so.delivered == False

def test_mongo_stuffy_node():
    reset_database()
    n = StuffyNode(email_addr='hugh_dowding@chain.home', uri=MONGO_URI_DOWDING)
    assert isinstance(n, StuffyNode)
    assert n._db_name == 'stuffy'
    assert n._email_addr == 'hugh_dowding@chain.home'
    assert n._write_collection_name == "new"
    assert n._read_collection_name == "hugh_dowding"

def test_send():
    reset_database()
    n = StuffyNode(email_addr='hugh_dowding@chain.home', uri=MONGO_URI_DOWDING)
    so = StuffyObject(DOS_TEST_2)
    so.recipients = ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    result = n.send(so)
    assert result.acknowledged
    post_office = StuffyNode(email_addr='air_marshall@chain.home', uri=MONGO_ADMIN_URI)
    so_in_transit = post_office._write_collection.find_one({})
    assert so_in_transit['sender'] == 'hugh_dowding@chain.home'
    assert so_in_transit['channel'] == 'stuffy'
    assert so_in_transit['recipients'][0] == 'robert_watt@chain.home'
    assert so_in_transit['recipients'][1] == 'anthony_wilkins@chain.home'
    assert not so_in_transit['delivered']
    assert not so_in_transit['already_read']

def test_deliver_stuck_messages():
    reset_database()
    # Send a message to 2 recipients
    hugh = StuffyNode(email_addr='hugh_dowding@chain.home.com', uri=MONGO_URI_DOWDING)
    so = StuffyObject(DOS_TEST_2)
    so.recipients = ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    result = hugh.send(so)
    # Run deliver_stuck_messages as an admin
    sleep(2)
    post_office = StuffyNode(email_addr='air_marshall@chain.home', uri=MONGO_ADMIN_URI)
    age_in_seconds = 1
    result = post_office.deliver_stuck_messages(age_in_seconds)
    # Check that one Stuffy Object was delivered
    assert result == 1
    # check that "delivered" is set to true in the _write_collection
    so_in_transit = post_office._db['new'].find({})[0]
    assert so_in_transit['delivered']

    #  Check that the SO was sent to the recipients
    result = post_office._db['robert_watt'].find({})
    assert isinstance(result, Cursor)
    for so_in_transit in result:
        assert so_in_transit['delivered']
        assert so_in_transit['sender'] == 'hugh_dowding@chain.home.com'
        assert so_in_transit['dict_of_stuff']['subject'] == "This is the test!"
        assert so_in_transit['dict_of_stuff']['message'] == "I say chaps!"
        assert so_in_transit['recipients'] == ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    result = post_office._db['anthony_wilkins'].find({})
    assert isinstance(result, Cursor)
    for so_in_transit in result:
        assert so_in_transit['delivered']
        assert so_in_transit['sender'] == 'hugh_dowding@chain.home.com'
        assert so_in_transit['dict_of_stuff']['subject'] == "This is the test!"
        assert so_in_transit['dict_of_stuff']['message'] == "I say chaps!"
        assert so_in_transit['recipients'] == ['robert_watt@chain.home', 'anthony_wilkins@chain.home']

def test_deliver():
    reset_database()
    hugh = StuffyNode(email_addr='hugh_dowding@chain.home.com', uri=MONGO_URI_DOWDING)
    so = StuffyObject(DOS_TEST_2)
    so.recipients = ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    result = hugh.send(so)
    post_office = StuffyNode(email_addr='air_marshall@chain.home', uri=MONGO_ADMIN_URI)
    new_stuff = post_office._db['new'].find({})
    for so_in_transit in new_stuff:
        result = post_office.deliver(so_in_transit['_id'])
        assert result.acknowledged
    # Check to see if deliver worked
    result = post_office._db['robert_watt'].find({})
    assert isinstance(result, Cursor)
    for so_in_transit in result:
        assert so_in_transit['delivered']
        assert so_in_transit['sender'] == 'hugh_dowding@chain.home.com'
        assert so_in_transit['dict_of_stuff']['subject'] == "This is the test!"
        assert so_in_transit['dict_of_stuff']['message'] == "I say chaps!"
        assert so_in_transit['recipients'] == ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    result = post_office._db['anthony_wilkins'].find({})
    assert isinstance(result, Cursor)
    for so_in_transit in result:
        assert so_in_transit['delivered']
        assert so_in_transit['sender'] == 'hugh_dowding@chain.home.com'
        assert so_in_transit['dict_of_stuff']['subject'] == "This is the test!"
        assert so_in_transit['dict_of_stuff']['message'] == "I say chaps!"
        assert so_in_transit['recipients'] == ['robert_watt@chain.home', 'anthony_wilkins@chain.home']


def test_receive():
    reset_database()
    hugh = StuffyNode(email_addr='hugh_dowding@chain.home.com', uri=MONGO_URI_DOWDING)
    so = StuffyObject(DOS_TEST_2)
    so.recipients = ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    send_result = hugh.send(so)
    post_office = StuffyNode(email_addr='air_marshall@chain.home', uri=MONGO_ADMIN_URI)
    result = post_office.deliver(send_result.inserted_id)
    robert = StuffyNode(email_addr='robert_watt@chain.home.com', uri=MONGO_URI_WATT)
    so_list = robert.receive()
    assert isinstance(so_list, list)
    so = so_list[0]
    assert isinstance(so, StuffyObject)
    assert so.sender == "hugh_dowding@chain.home.com"
    assert so.dict_of_stuff["subject"] == "This is the test!"
    assert so.recipients == ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    assert so.already_read
    assert so.delivered

def test_delete():
    reset_database()
    hugh = StuffyNode(email_addr='hugh_dowding@chain.home.com', uri=MONGO_URI_DOWDING)
    so = StuffyObject(DOS_TEST_2)
    so.recipients = ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    send_result = hugh.send(so)
    post_office = StuffyNode(email_addr='air_marshall@chain.home', uri=MONGO_ADMIN_URI)
    result = post_office.deliver(send_result.inserted_id)
    robert = StuffyNode(email_addr='robert_watt@chain.home.com', uri=MONGO_URI_WATT)
    so_list = robert.receive()
    result = robert.delete(so_list[0].uid)
    assert result

def test_clean_up_new_messages():
    reset_database()
    # Send a message to 2 recipients
    hugh = StuffyNode(email_addr='hugh_dowding@chain.home.com', uri=MONGO_URI_DOWDING)
    so = StuffyObject(DOS_TEST_2)
    so.recipients = ['robert_watt@chain.home', 'anthony_wilkins@chain.home']
    send_result = hugh.send(so)
    # Run clean_up as an admin
    sleep(2)
    post_office = StuffyNode(email_addr='air_marshall@chain.home', uri=MONGO_ADMIN_URI)
    post_office._write_collection.update_one({"_id": send_result.inserted_id}, {"$set": {"delivered": True}})
    age_in_seconds = 1
    result = post_office.clean_up(age_in_seconds)
    # See if it delete one message
    assert result == 1
    # Check to see if message deleted
    result = post_office._db['new'].find({})
    assert result.retrieved == 0


if __name__ == '__main__':
    test_clean_up_new_messages()

