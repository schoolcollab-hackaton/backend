from tortoise.models import Model
from tortoise import fields
from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime
from enum import Enum

class User(Model):
    id = fields.IntField(pk=True)
    nom = fields.CharField(max_length=100)
    email = fields.CharField(max_length=200, unique=True)
    phone = fields.CharField(max_length=20, null=True)
    avatar = fields.TextField(null=True)
    password = fields.TextField(null=False)
    is_owner = fields.BooleanField(default=False)
    is_passenger = fields.BooleanField(default=True)
    created_at = fields.DatetimeField(auto_now_add=True)
    updated_at = fields.DatetimeField(auto_now=True)