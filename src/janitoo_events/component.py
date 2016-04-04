# -*- coding: utf-8 -*-
"""The 1-wire Bus
It handle all communications to the onewire bus

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
__copyright__ = "Copyright © 2013-2014-2015-2016 Sébastien GALLET aka bibi21000"

# Set default logging handler to avoid "No handler found" warnings.
import logging
logger = logging.getLogger(__name__)

import os
import time
import datetime

from janitoo.bus import JNTBus
from janitoo.value import JNTValue, value_config_poll
from janitoo.node import JNTNode
from janitoo.component import JNTComponent

from janitoo_events.thread import OID

##############################################################
#Check that we are in sync with the official command classes
#Must be implemented for non-regression
from janitoo.classes import COMMAND_DESC

COMMAND_METER = 0x0032
COMMAND_CONFIGURATION = 0x0070

assert(COMMAND_DESC[COMMAND_METER] == 'COMMAND_METER')
assert(COMMAND_DESC[COMMAND_CONFIGURATION] == 'COMMAND_CONFIGURATION')
##############################################################

def make_biocycle(**kwargs):
    return BiocycleComponent(**kwargs)

class BiocycleComponent(JNTComponent):
    """ A 'bio' cyclecomponent"""

    def __init__(self, bus=None, addr=None, **kwargs):
        """
        """
        oid = kwargs.pop('oid', '%s.biocycle'%OID)
        name = kwargs.pop('name', "Bio cycle")
        product_name = kwargs.pop('product_name', "Bio cycle simulator")
        JNTComponent.__init__(self, oid=oid, bus=bus, addr=addr, name=name, hearbeat=60,
                product_name=product_name, **kwargs)
        logger.debug("[%s] - __init__ node uuid:%s", self.__class__.__name__, self.uuid)
        uuid="cycle"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The number of days in the cycle',
            label='Days',
            default=kwargs.pop('cycle', 28),
        )
        uuid="current"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The current day in the cycle',
            label='Day',
            default=kwargs.pop('current', 11),
        )
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="max"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The max minutes for the cycle in a day',
            label='Max',
            default=kwargs.pop('max', 60),
        )
        uuid="min"
        self.values[uuid] = self.value_factory['config_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The min minutes for the cycle in a day',
            label='Min',
            default=kwargs.pop('min', 0),
        )
        uuid="last_rotate"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The last date of rotation',
            label='Last',
        )
        poll_value = self.values[uuid].create_poll_value(default=1800)
        self.values[poll_value.uuid] = poll_value
        uuid="midi"
        self.values[uuid] = self.value_factory['config_string'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The hour of the midi for the cycle',
            label='Mid.',
            default=kwargs.pop('midi', '16:30'),
        )
        uuid="duration"
        self.values[uuid] = self.value_factory['sensor_basic_integer'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The duration in minutes of the cycle for the current day',
            label='Duration',
            get_data_cb=self.duration,
        )
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="factor_day"
        self.values[uuid] = self.value_factory['sensor_basic_float'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The factor for today. A value for -1 to 1',
            label='Today',
            get_data_cb=self.factor_day,
        )
        poll_value = self.values[uuid].create_poll_value(default=3600)
        self.values[poll_value.uuid] = poll_value
        uuid="factor_now"
        self.values[uuid] = self.value_factory['sensor_basic_float'](options=self.options, uuid=uuid,
            node_uuid=self.uuid,
            help='The factor for now. A value for -1 to 1',
            label='Now',
            get_data_cb=self.factor_now,
        )
        poll_value = self.values[uuid].create_poll_value(default=300)
        self.values[poll_value.uuid] = poll_value

    def current_rotate(self):
        """Rotate the current day to go ahead in the cycle
        """
        self.values['last_rotate'].set_data_index(index=0, data=datetime.datetime.now().strftime('%m/%d/%Y %H:%M:%S'))
        nextd = self.values['current'].get_data_index(index=0)+1
        if nextd >= self.values['cycle'].data:
            self.values['current'].set_data_index(index=0, data=0)
        else:
            self.values['current'].set_data_index(index=0, data=nextd)
        if self.node is not None:
            self._bus.nodeman.publish_poll(self.mqttc, self.values['current'])
            self._bus.nodeman.publish_poll(self.mqttc, self.values['last_rotate'])

    def check_heartbeat(self):
        """Check that the component is 'available'
        """
        return True

    def factor_day(self, node_uuid, index):
        """Return the day factor
        """
        data = None
        try:
            data = float(self.get_cycle_factor(index=index))
            if data<-1:
                data = -1.0
            elif data>1:
                data = 1.0
        except :
            logger.exception('Exception when calculationg day factor')
        return data

    def start(self, mqttc):
        """Start the component. Can be used to start a thread to acquire data.

        """
        self._bus.nodeman.add_daily_job(self.current_rotate)
        return JNTComponent.start(self, mqttc)

    def stop(self):
        """Stop the component.

        """
        self._bus.nodeman.remove_daily_job(self.current_rotate)
        return JNTComponent.stop(self)

    def factor_now(self, node_uuid, index):
        """Return the instant factor
        """
        data = None
        try:
            data = float(self.get_hour_factor(index=index))
            if data<-1:
                data = -1.0
            elif data>1:
                data = 1.0
        except :
            logger.exception('Exception when calculationg now factor')
        return data

    def duration(self, node_uuid, index):
        '''Return the cycle duration in the day
        '''
        data = None
        try:
            data = int(self.get_cycle_duration(index=index))
        except :
            logger.exception('Exception when calculationg duration')
        return data

    def _get_factor(self, current, cycle):
        """Calculate the factor"""
        return 2.0 * (current - (cycle / 2.0)) / cycle

    def get_cycle_factor(self, index=0):
        """Get the factor related to day cycle
        """
        return self._get_factor(self.values['current'].get_data_index(index=index), self.values['cycle'].get_data_index(index=index))

    def get_cycle_duration(self, index=0):
        """Get the duration in minutes of the cycle for today"""
        dfact = abs(self.get_cycle_factor())
        dlen = self.values['min'].get_data_index(index=index) + ( self.values['max'].get_data_index(index=index) - self.values['min'].get_data_index(index=index)) * dfact
        return dlen

    def get_hour_factor(self, index=0, nnow=None):
        """Get the factor
        """
        if nnow is None:
            nnow = datetime.datetime.now()
        hh, mm = self.values['midi'].get_data_index(index=index).split(':')
        midd = nnow.replace(hour=int(hh), minute=int(mm))
        tdur = self.get_cycle_duration()
        cdur = int(tdur/2)
        start = midd - datetime.timedelta(minutes=cdur)
        stop = midd + datetime.timedelta(minutes=cdur)
        if nnow<start or nnow>stop:
            return 0
        elapsed = (nnow - start).total_seconds()/60
        return 1-abs(self._get_factor(int(elapsed), int(tdur)))

    def get_status(self, index=0, nnow=None):
        """Get the current status
        """
        if nnow is None:
            nnow = datetime.datetime.now()
        hh, mm = self.values['midi'].get_data_index(index=index).split(':')
        midd = nnow.replace(hour=int(hh), minute=int(mm))
        cdur = int(self.get_cycle_duration()/2)
        start = midd - datetime.timedelta(minutes=cdur)
        stop = midd + datetime.timedelta(minutes=cdur)
        if nnow<start or nnow>stop:
            return False
        return True
