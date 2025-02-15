from r2a.ir2a import IR2A
import time
from player.parser import *
from math import e

class R2AMpegDash(IR2A):
    def __init__(self, id):
        IR2A.__init__(self, id)
        self.throughputs_estimated = [] # Lista para armazenar os throughput estimados
        self.parsed_mpd = '' # Variável para armazenar o MPD analisado
        self.request_time = 0 # Tempo da requisição
        self.qi = [] # Lista para armazenar as qualidades disponíveis
        self.past_throughput = 0 # Armazena o throughput do segmento anterior
        self.T_s = 0 # Armazena o throughput do segmento atual
        self.p_value = 0 # Valor de p calculado
        self.delta_value = 0 # Valor de delta (δ)
        self.i = 0 # Contador de segmentos

    def calc_p_value(self, T_s): # Calcula o valor de p com base no throughput do segmento i e no estimado
        #print(f'clp:{self.throughputs_estimated[-1]}')
        return((abs(T_s - self.throughputs_estimated[-1]))/self.throughputs_estimated[-1]) #valor de p

    def calc_delta_value(self, p): # Calcula o valor de delta usando uma função logística, proposta no artigo
        k = 21
        p_0 = 0.2
        return(1/(1+e**(-k*(p-p_0)))) # Função logística para calcular delta

    def handle_xml_request(self, msg): # Manipula a requisição XML
        #print('xmlReq')
        self.request_time = time.perf_counter() # Registra o tempo da requisição
        #print(self.request_time)
        self.send_down(msg) #Envia a mensagem para baixo (ConnectionHandler)

    def handle_xml_response(self, msg):  # Manipula a resposta XML
        t = time.perf_counter() - self.request_time # Calcula o tempo de resposta
        #print('Rxml')
        self.parsed_mpd = parse_mpd(msg.get_payload()) # Analisa o MPD da mensagem
        self.qi = self.parsed_mpd.get_qi() # Obtém as qualidades disponíveis
        #self.throughputs_estimated.append(msg.get_bit_length()/t)
        self.past_throughput = msg.get_bit_length()/t  # Calcula o throughput da resposta
        print(f'throughputxml: {msg.get_bit_length()/t}')
        #print(f'length {msg.get_bit_length()}')
        self.send_up(msg) #Envia a mensagem para baixo (Player)

    def handle_segment_size_request(self, msg): # Manipula a requisição de tamanho do segmento
        self.i = self.i + 1  # Incrementa o contador de segmentos
        print()
        self.request_time = time.perf_counter() # Registra o tempo da requisição do segmento
        # i é o segmento a ser baixado
        mi = 0.3 # Margem de segurança para o bitrate
        print(self.throughputs_estimated)
        print(self.past_throughput)
        if len(self.throughputs_estimated)==0: # Define o bitrate constraint R_c
            R_c = self.past_throughput # Se não houver estimativas, usa o throughput passado
        else:
            R_c = ((1-mi) * self.throughputs_estimated[-1]) #calcula o bitrate constraint
            # que é uma margem, para que o bitrate da proóxima qualidade não seja no limite do thoughput esperado.
        #print(f'Rc: {R_c}, thr: {self.throughputs_estimated[-1]},{self.i}')
        selected_qi = self.qi[0] # Seleciona a qualidade mais baixa inicialmente i=0
        if self.i > 1:
            for n in self.qi: # Seleciona a qualidade que é menor que R_c
                if R_c > n:
                    selected_qi = n

        msg.add_quality_id(selected_qi) # Adiciona a qualidade selecionada à mensagem
        self.send_down(msg) # Envia a mensagem para baixo

    def handle_segment_size_response(self, msg): # Manipula a resposta de tamanho do segmento
        print()
        t = time.perf_counter() - self.request_time  # Calcula o tempo de resposta
        self.T_s = msg.get_bit_length() / t  # Calcula o Throughput para o segmento atual i
        if self.i > 2:
            print(f' i{self.i}: {self.past_throughput}')
            self.p_value = self.calc_p_value(self.T_s)  # Calcular valor de p
            self.delta_value = self.calc_delta_value(self.p_value)  # Calcular valor de delta passando p como parametro
            print(f'>>delta:{self.delta_value}, p:{self.p_value}, ts{self.T_s},T_epast:{self.throughputs_estimated[-1]} tspast{self.past_throughput},i:{self.i}')
            """Estima o throughput para i+1, o próximo segmento, usando T_s(i)
            T_s: Throughput do Segmento atual
            """
            print(self.throughputs_estimated)
            print(self.throughputs_estimated[self.i - 2])
            #print(self.T_s)
            self.throughputs_estimated.append(((1-self.delta_value) * self.throughputs_estimated[self.i - 2]) + self.delta_value*(self.T_s))
            self.past_throughput = self.T_s ## Atualiza o throughput passado para que possa ser usado depois para calcular o p
            self.send_up(msg)
        elif self.i == 1:
            print(f' i{self.i}: {self.past_throughput}')
            self.throughputs_estimated.append(self.T_s) # Armazena o throughput do primeiro segmento
            self.past_throughput = self.T_s #Atualiza o throughput passado
            self.send_up(msg)
        else: #i==2
            print(f' i{self.i}: {self.past_throughput}')
            print(f'>>delta:{self.delta_value}, p:{self.p_value}, ts{self.T_s},T_epast:{self.throughputs_estimated[-1]} tspast{self.past_throughput},i:{self.i}')
            self.throughputs_estimated.append(self.past_throughput)#colocar ts para teste #Armazena o throughput do segundo segmento
            self.past_throughput = self.T_s  #Atualiza o throughput passado para calcular o valor de p do proximo segmento
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
        self.p=abs((self.lastT-self.EstimatedT)/self.EstimatedT)

    def calcDelta(self):
        self.delta = 1/(1+math.exp(-self.k*(self.p-self.p0)))