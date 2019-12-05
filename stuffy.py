from pymongo import MongoClient
from datetime import datetime, tzinfo
import time
import json

class StuffyObject(object):
    """
    Instantiates an object that contains the Dictonary Of Stuff, status and addressing info.
    """
    def __init__(self, dict_of_stuff, channel='stuffy'):
        self.uid = None
        self.sender = ""
        self.recipients = []
        self.channel = channel
        self.already_read = False
        self.delivered = False
        self.dict_of_stuff = dict_of_stuff

class StuffyNode(object):
    """
    Objects of this type setup a connection with a mongoDB database that is used to transfer a Stuffy Object to
    other programs using email addresses for routing to the correct recipient.
    """

    def __init__(self, email_addr, db='stuffy', write_collection='new', uri=''):
        """
        Create a Stuffy node that can be used to send and receive dos objects.

        :param email_addr:
        :param db: The mongodB database name
        :param write_collection: The name of the mongdDB collection where new StuffObjects objects are written to
        :param uri: The mongoDB URI used for access to the database and its collections.
        """
        self._email_addr = email_addr
        self._uri = uri
        # TODO!  Do we need to keep the names?
        self._db_name = db
        self._write_collection_name = write_collection
        self._read_collection_name = email_addr[0:email_addr.find('@')]  # Extract collection name from email address
        self._db = MongoClient(self._uri)[self._db_name]
        self._write_collection = self._db[self._write_collection_name]
        self._read_collection = self._db[self._read_collection_name]

    def send(self, so):
        """
        Send the StuffyObject.

        :param so: A StuffyObject
        :return Success: True/False

        """
        insert_result = None
        so.sender = self._email_addr
        insert_result = self._write_collection.insert_one(so.__dict__)
        return insert_result

    def receive(self):
        """
        Get all Stuffy Objects from the "..." collection that have not yet been read.
        :return so_list: A list of StuffyObjects
        """
        so_list = []
        incoming = list(self._read_collection.find({"already_read": False}))
        for so_in_transit in incoming:
            so = StuffyObject(so_in_transit['dict_of_stuff'])
            so.uid = so_in_transit['_id']
            so.recipients = so_in_transit['recipients']
            so.sender = so_in_transit['sender']
            so.already_read = True
            so.delivered = True
            so_list.append(so)
            self._read_collection.update_one({"_id": so_in_transit["uid"]}, {"$set": {"already_read": True}})
        return so_list

    def delete(self, uid):
        """
        Remove a single dos object that have been read.
        :param: uid:  The ObjectId of the StuffyObject to be deleted from the "..." collection
        :return: True/False
        """
        result = self._read_collection.delete_one({"_id": uid, "already_read": True})
        return result.acknowledged

    def deliver(self, uid):
        """
        Copy a single SO from the write_collection to the read_collection(s) of all recipients.
        param: uid : The _id of the mongoDB document to be delivered

        """
        insert_result = None
        for so_in_transit in self._write_collection.find({"_id": uid}):
            for recipient in so_in_transit['recipients']:
                recipient_collection_name = recipient[0:recipient.find('@')]  # Extract from email address
                recipient_collection = self._db[recipient_collection_name]
                so_in_transit["delivered"] = True
                insert_result = recipient_collection.insert_one(so_in_transit)
            self._write_collection.update_one({"_id": so_in_transit["_id"]}, {"$set": {"delivered": True}})
        return insert_result

    def clean_up(self, age_in_seconds=10) -> int:
        """
        Remove all messages from the write_collection that have been "delivered" and are older than age_in_seconds
        :return: num_so_deleted: Number of SOs deleted
        """
        so_list = self._write_collection.find({"delivered": True})
        epoch_time_now = time.time()
        num_so_deleted = 0
        for so_in_transit in so_list:
            epoch_time_written = so_in_transit['_id'].generation_time.timestamp()
            if (epoch_time_now - epoch_time_written) >= age_in_seconds:
                self._write_collection.delete_one({'_id': so_in_transit['_id']})
                num_so_deleted += 1
        return num_so_deleted

    def deliver_stuck_messages(self, age_in_seconds=10) -> int:
        """
        Send all messages in the "..." that have not been "delivered" and are older than "age_in_seconds".
        This function is to be run by a sentinel to ensure that no messages get "stuck".

        param: age_in_seconds:  Age that a SO needs to be before clean_up will deliver it.

        :return: num_so_delivered: The number of Stuffy Objects delivered during clean-up.
        """

        so_list = self._write_collection.find({"delivered": False})
        epoch_time_now = time.time()
        num_so_delivered = 0
        for so_in_transit in so_list:
            epoch_time_written = so_in_transit['_id'].generation_time.timestamp()
            if (epoch_time_now - epoch_time_written) >= age_in_seconds:
                self.deliver(so_in_transit['_id'])
                num_so_delivered += 1
        return num_so_delivered


