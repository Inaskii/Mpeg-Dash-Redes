from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean
import math


class R2AMpegDash(IR2A):
    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = []
        self.request_time = 0
        self.qi = []

        self.delta_min = 0.05
        self.k = 21
        self.p0 = 0.2
        self.EstimatedT = 1
        self.delta = 1
        self.p=None


    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)


    def handle_xml_response(self, msg):

        parsed_mpd = parse_mpd(msg.get_payload())
        self.qi = parsed_mpd.get_qi()

        t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / t)

        self.send_up(msg)


    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        self.calcP()
        self.calcDelta()
        self.EstimatedT = self.estimate_throughput()


        
        selected_qi = self.qi[0]
        for i in self.qi:
            if self.EstimatedT > i:
                selected_qi = i



        msg.add_quality_id(selected_qi)
        self.send_down(msg)

    def handle_segment_size_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / t)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    def estimate_throughput(self):
        if len(self.throughputs) < 2:
            return self.throughputs[-1]
        
        return (1 - self.delta) * self.EstimatedT + self.delta * self.throughputs[-1]
    
    def calcP(self):
        self.p=abs((self.throughputs[-1]-self.EstimatedT)/self.EstimatedT)

    def calcDelta(self):
        self.delta = 1/(1+math.exp(-self.k*(self.p-self.p0)))