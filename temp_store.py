from telegram.ext import CallbackContext
from constants import *
from typing import Tuple, Any

class Store:
    """this is a glorified tree with a dictionary instead of a list of children"""
    def __init__(self):
        self.data = None
        self.children = {}
    
    def set_data(self, data):
        self.data = data
        return 1
    
    def store_data(self, data, labels):
        if not labels:
            return self.set_data(data)
        label = labels.pop(0)
        if label not in self.children.keys():
            self.children[label] = Store()
        return self.children[label].store_data(data, labels)
    
    def retrieve_data(self, labels):
        if not labels:
            return self.data
        label = labels.pop(0)
        if label not in self.children.keys():
            return None
        return self.children[label].retrieve_data(labels)
    
    def clear_data(self, labels):
        if not labels:
            return self.clear_all_data()
        label = labels.pop(0)
        if label not in self.children.keys():
            return -1
        return self.children[label].clear_data(labels)
    
    def clear_all_data(self):
        self.data = None
        for child in self.children.values():
            child.clear_all_data()
        self.children.clear()
        return 1

def store_temp_data(context: CallbackContext, data: Any, labels: Tuple[str, ...]) -> int:
    try:
        if TEMP_STORE not in context.user_data.keys():
            context.user_data[TEMP_STORE] = Store()
        temp_store = context.user_data[TEMP_STORE]
        return temp_store.store_data(data, labels)
    except Exception as e:
        print(f"store_temp_data()\n{e}")
        return -1

def get_temp_data(context: CallbackContext, labels: Tuple[str, ...]) -> Any:
    if TEMP_STORE not in context.user_data.keys():
        context.user_data[TEMP_STORE] = Store()
    temp_store = context.user_data[TEMP_STORE]
    return temp_store.retrieve_data(labels)

def clear_temp_data(context: CallbackContext, labels: Tuple[str, ...] = ()) -> int:
    try:
        temp_store = context.user_data[TEMP_STORE]
        temp_store.clear_data(labels)
    except Exception as e:
        print(f"clear_temp_data()\n{e}")
        return -1