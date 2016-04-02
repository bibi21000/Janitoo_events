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

from nose_parameterized import parameterized

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

    @parameterized.expand([
        (28, 0, -1),
        (28, 14, 0),
        (28, 28, 1),
    ])
    def test_get_cycle_factor_constant(self, cycle, current, result):
        self.assertEqual(BiocycleComponent(cycle=cycle, current=current).get_cycle_factor(), result)

    @parameterized.expand([
        (28, 0, 10),
        (28, 6, 10),
        (28, 14, 10),
        (28, 17, 10),
        (28, 28, 10),
        (28, 0, 7),
        (28, 6, 7),
        (28, 14, 7),
        (28, 17, 7),
        (28, 28, 7),
        (28, 0, 2),
        (28, 6, 2),
        (28, 14, 2),
        (28, 17, 2),
        (28, 28, 2),
    ])
    def test_get_cycle_factor_factor(self, cycle, current, factor):
        self.assertEqual(
            BiocycleComponent(cycle=cycle, current=current).get_cycle_factor(),
            BiocycleComponent(cycle=cycle*factor, current=current*factor).get_cycle_factor()
            )

    @parameterized.expand([
        (28, 0, 0, 60, 60),
        (28, 14, 0, 60, 0),
        (28, 28, 0, 60, 60),
    ])
    def test_get_cycle_duration_constant(self, cycle, current, mmin, mmax, result):
        self.assertEqual(BiocycleComponent(cycle=cycle, current=current, min=mmin, max=mmax).get_cycle_duration(), result)

    @parameterized.expand([
        (28, 0, 0, 160, 10),
        (28, 6, 0, 160, 10),
        (28, 14, 0, 160, 10),
        (28, 17, 0, 160, 10),
        (28, 28, 0, 160, 10),
        (28, 0, 60, 160, 10),
        (28, 6, 60, 160, 10),
        (28, 14, 60, 160, 10),
        (28, 17, 60, 160, 10),
        (28, 28, 60, 160, 10),
        (28, 0, 0, 60, 7),
        (28, 6, 0, 60, 7),
        (28, 14, 0, 60, 7),
        (28, 17, 0, 60, 7),
        (28, 28, 0, 60, 7),
        (28, 0, 0, 30, 2),
        (28, 6, 0, 30, 2),
        (28, 14, 0, 30, 2),
        (28, 17, 0, 30, 2),
        (28, 28, 0, 30, 2),
    ])
    def test_get_cycle_duration_factor(self, cycle, current, mmin, mmax, factor):
        self.assertEqual(
            BiocycleComponent(cycle=cycle, current=current, min=mmin, max=mmax).get_cycle_duration(),
            BiocycleComponent(cycle=cycle*factor, current=current*factor, min=mmin, max=mmax).get_cycle_duration()
            )

    @parameterized.expand([
        (28, 0, 0, 60),
        (28, 14, 0, 60),
        (28, 28, 0, 60),
        (28, 0, 60, 120),
        (28, 14, 60, 120),
        (28, 28, 60, 120),
    ])
    def test_get_factor_middle(self, cycle, current, mmin, mmax):
        nnow = datetime.datetime.now()
        mbefore = nnow-datetime.timedelta(minutes=mmin/2+mmax/2+1+mmax/4)
        before = nnow-datetime.timedelta(minutes=mmin/2+mmax/2+1)
        mafter = nnow+datetime.timedelta(minutes=mmin/2+mmax/2+1-mmax/4)
        after = nnow+datetime.timedelta(minutes=mmin/2+mmax/2+1)
        self.assertEqual(
            BiocycleComponent(
                cycle=cycle, current=current, min=mmin, max=mmax,
                midi="%s:%s"%(before.hour,before.minute)).get_hour_factor(nnow=nnow),
            0
            )
        self.assertNotEqual(
            BiocycleComponent(
                cycle=cycle, current=current, min=mmin, max=mmax,
                midi="%s:%s"%(mbefore.hour,mbefore.minute)).get_hour_factor(nnow=nnow),
            0
            )
        self.assertEqual(
            BiocycleComponent(
                cycle=cycle, current=current, min=mmin, max=mmax,
                midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow),
            1
            )
        self.assertNotEqual(
            BiocycleComponent(
                cycle=cycle, current=current, min=mmin, max=mmax,
                midi="%s:%s"%(mafter.hour,mafter.minute)).get_hour_factor(nnow=nnow),
            0
            )
        self.assertEqual(
            BiocycleComponent(
                cycle=cycle, current=current, min=mmin, max=mmax,
                midi="%s:%s"%(after.hour,after.minute)).get_hour_factor(nnow=nnow),
            0
            )

    def tt_011_factor_middle_cycle(self):
        nnow = datetime.datetime.now()
        self.assertEqual(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%((nnow-datetime.timedelta(hours=1)).hour,nnow.minute)).get_hour_factor(nnow=nnow), 0)
        self.assertEqual(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%((nnow+datetime.timedelta(hours=1)).hour,nnow.minute)).get_hour_factor(nnow=nnow), 0)
        self.assertEqual(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow), 1)
        self.assertGreater(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow+datetime.timedelta(minutes=9)),
                           BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow+datetime.timedelta(minutes=12)))
        self.assertGreater(BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow-datetime.timedelta(minutes=9)),
                           BiocycleComponent(cycle=28, current=0, min=0, max=60, midi="%s:%s"%(nnow.hour,nnow.minute)).get_hour_factor(nnow=nnow-datetime.timedelta(minutes=12)))
