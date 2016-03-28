# -*- coding: utf-8 -*-

"""Unittests for Janitoo-Roomba Server.
"""
__license__ = """
    This file is part of Janitoo.

    Janitoo is free software: you can redistribute it and/or modify
    it under the terms of the GNU General Public License as published by
    the Free Software Foundation, either version 3 of the License, or
    (at your option) any later version.

    Janitoo is distributed in the hope that it will be useful,
    but WITHOUT ANY WARRANTY; without even the implied warranty of
    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
    GNU General Public License for more details.

    You should have received a copy of the GNU General Public License
    along with Janitoo. If not, see <http://www.gnu.org/licenses/>.

"""
__author__ = 'Sébastien GALLET aka bibi21000'
__email__ = 'bibi21000@gmail.com'
__copyright__ = "Copyright © 2013-2014-2015 Sébastien GALLET aka bibi21000"

import warnings
warnings.filterwarnings("ignore")

import sys, os
import time, datetime
import unittest
import threading
import logging
from logging.config import fileConfig as logging_fileConfig
from pkg_resources import iter_entry_points
import datetime
import mock

from janitoo_nosetests import JNTTBase
from janitoo_nosetests.server import JNTTServer, JNTTServerCommon
from janitoo_nosetests.thread import JNTTThread, JNTTThreadCommon
from janitoo_nosetests.thread import JNTTThreadRun, JNTTThreadRunCommon
from janitoo_nosetests.component import JNTTComponent, JNTTComponentCommon

from janitoo.utils import json_dumps, json_loads
from janitoo.utils import HADD_SEP, HADD
from janitoo.utils import TOPIC_HEARTBEAT
from janitoo.utils import TOPIC_NODES, TOPIC_NODES_REPLY, TOPIC_NODES_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.utils import TOPIC_BROADCAST_REPLY, TOPIC_BROADCAST_REQUEST
from janitoo.options import JNTOptions
from janitoo.runner import jnt_parse_args

from janitoo_events.component import BiocycleComponent
from janitoo_events.thread import EventsBus

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_DISCOVERY = 0x5000

assert(COMMAND_DESC[COMMAND_DISCOVERY] == 'COMMAND_DISCOVERY')
##############################################################

class TestCyclicEvent(JNTTBase):
    """Test
    """

    def test_001_get_cycle_factor(self):
        self.assertEqual(BiocycleComponent(cycle=28, current=0).get_cycle_factor(), -1)
        self.assertEqual(BiocycleComponent(cycle=28, current=14).get_cycle_factor(), 0)
        self.assertEqual(BiocycleComponent(cycle=28, current=28).get_cycle_factor(), 1)
        self.assertEqual(BiocycleComponent(cycle=28, current=0).get_cycle_factor(),BiocycleComponent(cycle=280, current=0).get_cycle_factor())
        self.assertEqual(BiocycleComponent(cycle=28, current=14).get_cycle_factor(),BiocycleComponent(cycle=280, current=140).get_cycle_factor())
        self.assertEqual(BiocycleComponent(cycle=28, current=28).get_cycle_factor(),BiocycleComponent(cycle=280, current=280).get_cycle_factor())
        self.assertEqual(BiocycleComponent(cycle=28, current=18).get_cycle_factor(),BiocycleComponent(cycle=280, current=180).get_cycle_factor())
        self.assertEqual(BiocycleComponent(cycle=28, current=7).get_cycle_factor(),BiocycleComponent(cycle=280, current=70).get_cycle_factor())

    def test_001_get_cycle_duration(self):
        self.assertEqual(BiocycleComponent(cycle=28, current=0, min=0, max=60).get_cycle_duration(), 60)
        self.assertEqual(BiocycleComponent(cycle=28, current=14, min=0, max=60).get_cycle_duration(), 0)
        self.assertEqual(BiocycleComponent(cycle=28, current=28, min=0, max=60).get_cycle_duration(), 60)
        self.assertEqual(BiocycleComponent(cycle=28, current=18, min=0, max=60).get_cycle_duration(),BiocycleComponent(cycle=280, current=180, min=0, max=60).get_cycle_duration())
        self.assertEqual(BiocycleComponent(cycle=28, current=7, min=0, max=60).get_cycle_duration(),BiocycleComponent(cycle=280, current=70, min=0, max=60).get_cycle_duration())
        self.assertEqual(BiocycleComponent(cycle=28, current=18, min=60, max=180).get_cycle_duration(),BiocycleComponent(cycle=280, current=180, min=60, max=180).get_cycle_duration())
        self.assertEqual(BiocycleComponent(cycle=28, current=7, min=120, max=420).get_cycle_duration(),BiocycleComponent(cycle=280, current=70, min=120, max=420).get_cycle_duration())

    def test_011_factor_middle_cycle(self):
        nnow = datetime.datetime.now()
        self.assertEqual(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%((nnow-datetime.timedelta(hours=1)).hour,nnow.minute)).get_hour_factor(nnow=nnow), 0)
        self.assertEqual(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%((nnow+datetime.timedelta(hours=1)).hour,nnow.minute)).get_hour_factor(nnow=nnow), 0)
        self.assertEqual(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow), 1)
        self.assertGreater(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow+datetime.timedelta(minutes=9)),
                           BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow+datetime.timedelta(minutes=12)))
        self.assertGreater(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow-datetime.timedelta(minutes=9)),
                           BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow-datetime.timedelta(minutes=12)))
