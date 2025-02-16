from r2a.ir2a import IR2A
from player.parser import *
import time
from statistics import mean
import math


class R2AMpegDash(IR2A):
    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs = []
        #lista de throughputs
        
        self.request_time = 0
        #tempo de requisição
        
        self.qi = []
        #lista de qualidades
        
        self.lastT = 0
        #ultimo throughput
        
        self.delta_min = 0.05
        #delta minimo
        
        self.k = 21
        #constante k 
        
        self.p0 = 0.2
        #p0
        
        self.EstimatedT = 1
        #throughput estimado
        
        self.delta = 1
        #delta
        
        self.p=0
        #Desvio normalizado de throughput
        
        self.parsed_mpd = None
        #mpd parseado
        
        self.mi = 0.35
        #margem de erro

    def handle_xml_request(self, msg):
        self.request_time = time.perf_counter()
        self.send_down(msg)


    def handle_xml_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length() / t)
        parsed_mpd = parse_mpd(msg.get_payload())
        self.parsed_mpd = parsed_mpd
        self.qi = parsed_mpd.get_qi()
        self.lastT = self.throughputs[-1]

        self.send_up(msg)


    def handle_segment_size_request(self, msg):
        self.request_time = time.perf_counter()
        self.nowT = msg.get_bit_length()

        self.calcP()
        self.calcDelta()
        self.EstimatedT = self.estimate_throughput()
        #calcula p, delta e depois estima throughput
        
        RC = (1-self.mi)* self.EstimatedT
        #calcula rc tendo em vista a margem de erro
        
        selected_qi = self.qi[0]
        for i in self.qi:
            if RC > i:
                selected_qi = i
        #seleciona a qualidade baseado no RC


        msg.add_quality_id(selected_qi)
        self.send_down(msg)
        
    def handle_segment_size_response(self, msg):
        t = time.perf_counter() - self.request_time
        self.throughputs.append(msg.get_bit_length()/t)
        self.send_up(msg)

    def initialize(self):
        pass

    def finalization(self):
        pass

    #calcula o throughput estimado
    def estimate_throughput(self):
        if len(self.throughputs) < 2:
            return self.throughputs[-1]
        
        return (1 - self.delta) * self.EstimatedT + self.delta * self.throughputs[-1]
    
    #Calcula P, chamado no artigo de "normalized throughput deviation"
    def calcP(self):
        self.p=abs((self.lastT-self.EstimatedT)/self.EstimatedT)
    
    #Calcula delta, variação que será usada para calcular o throughput estimado
    def calcDelta(self):
        self.delta = 1/(1+math.exp(-self.k*(self.p-self.p0)))