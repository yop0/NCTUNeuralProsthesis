import numpy as np
import scipy.integrate as scpi
import numpy.fft as fft

import matplotlib.pyplot as plt

class Stimuli(object): 
	def __init__(self, time_function, time_start, time_stop, resolution):
		self.time_start = time_start
		self.time_stop = time_stop
		self.resolution = resolution
		self.timepoints = np.linspace(self.time_start, self.time_stop, self.resolution)

		assert(callable(time_function))
		self.time_function = time_function

	def __call__(self, t): 
		return self.time_function(t)

class HodgkinHuxley(object): 

	def __init__(self, gNa=40., gK=35., gL=0.3, Cm=1.0, ENa=55.0, EK=-77.0, El=-65.): 
		# Mean sodium channel conductivity
		self.gNa = gNa
		# Sodium potential
		self.ENa = ENa

		# Mean potassium channel conductivity
		self.gK = gK
		# Potassium potential
		self.EK = EK

		# Mean leek conductivity
		self.gL = gL
		# Leak potential
		self.El = El

		# Membrane capacitance
		self.Cm = Cm

		# Current stimuli
		self.Iinj = None

	# Potassium channel

	def alpha_n(self, Vm): 
		# return (10 - Vm) / (100 * np.exp((10-Vm)/10) - 1)
		return 0.02 * (Vm - 25.) / (1 - np.exp(-(Vm - 25.)/9.))

	def beta_n(self, Vm): 
		# return 0.125 * np.exp(-Vm / 80)
		return -0.002 * (Vm - 25.)/ (1 - np.exp((Vm - 25.)/9.))

	def n_inf(self, Vm): 
		return self.alpha_n(Vm) / (self.alpha_n(Vm) + self.beta_n(Vm))

	# Potassium current
	def IK(self, Vm, n): 
		return self.gK * (Vm - self.EK) * (n**4) 


	# Sodium channels

	# Fast channel 
	def alpha_m(self, Vm): 
		# return (25 - Vm) / (10 * np.exp((25-Vm) / 10) - 1) 
		return 0.182 * (Vm + 35.) / ( 1. - np.exp(-(Vm + 35.)/9.))

	def beta_m(self, Vm): 
		# return 4 * np.exp(-Vm/18)
		return -0.124 * (Vm + 35.) / (1. - np.exp((Vm + 35.)/9.))

	def m_inf(self, Vm): 
		return self.alpha_m(Vm) / (self.alpha_m(Vm) + self.beta_m(Vm))

	# Slow channel
	def alpha_h(self, Vm): 
		# return 0.07*np.exp(-Vm/20)
		return 0.25 * np.exp(-(Vm + 90.) / 12.) 

	def beta_h(self, Vm): 
		# return 1 / (np.exp((30-Vm) / 10) +1)
		return 0.25 * np.exp((Vm + 62.) / 6.) / np.exp((Vm + 90.) / 12.)

	def h_inf(self, Vm): 
		return self.alpha_h(Vm) / (self.alpha_h(Vm) + self.beta_h(Vm))

	# Sodium current
	def INa(self, Vm, m, h): 
		return self.gNa * (m**3) * h * (Vm - self.ENa) 


	# Leak current 
	def Il(self, Vm): 
		return self.gL * (Vm - self.El)



	def compute_dydt(self, y, t): 
		Vm, n, m, h = y

		# print(Vm, self.IK(Vm, n), self.INa(Vm, m, h), self.Il(Vm))

		# Membrane potential dynamics
		dVmdt = (self.Iinj(t) - self.IK(Vm, n) - self.INa(Vm, m, h) - self.Il(Vm)) / self.Cm

		# Potassium channels dynamics
		dndt = self.alpha_n(Vm) * (1. - n) - self.beta_n(Vm) * n

		# Sodium channels dynamics
		# Fast channels
		dmdt = self.alpha_m(Vm) * (1. - m) - self.beta_m(Vm) * m
		# Slow channel
		dhdt = self.alpha_h(Vm) * (1. - h) - self.beta_h(Vm) * h

		dydt = [dVmdt, dndt, dmdt, dhdt]

		return dydt



	def stimulate(self, stimuli, Vm=-65., n=None, m=None, h=None):
		# The input stimuli is the injected current
		assert(isinstance(stimuli, Stimuli))
		self.Iinj = stimuli

		# Initial y point
		n_0 = n if n is not None else self.n_inf(Vm)
		m_0 = m if m is not None else self.m_inf(Vm)
		h_0 = h if h is not None else self.h_inf(Vm)

		y_0 = [Vm, n_0, m_0, h_0]
		# y_0 = [Vm_0, self.n_inf(Vm_0), self.m_inf(Vm_0), self.h_inf(Vm_0)]	

		# Integrate to get a time serie of y
		y = scpi.odeint(self.compute_dydt, y_0, stimuli.timepoints)

		return y

def fcy(timepoints, Vm, start): 
	first = None 
	second = None 
	done = False
	for i  in range(len(Vm[start:])): 
		v = Vm[start + i]
		if v > 0: 
			if done == False: 
				done = True
				if first is None: 
					first = i 
				elif second is None: 
					second = i
				else: 
					break
		elif v < 0 and done: 
			done = False

	if first is not None and second is not None: 
		return 1e4 / (timepoints[start + second] - timepoints[start + first])
	else: 
		return np.NaN

if __name__ == "__main__": 
	hh = HodgkinHuxley()


	# ampl = 2.

	rec = []

	valmin = 0.3
	valmax = 2.3
	valres = 100

	for ampl in np.linspace(valmin, valmax, valres):

		# y = hh.stimulate( Stimuli(lambda t : ampl if t >= 1 and t < 2 else 0.,0,100,10000) )
		s = Stimuli(lambda t : ampl if t > 0 else 0., -100. , 2000., 10000)
		# s = Stimuli(lambda t : 200.0 if t >= 1 and t < 2 else 0., 0., 20., 100000) 
		y = hh.stimulate( s )

		Vm = [y[i][0] for i in range(s.resolution)]
		n = [y[i][1] for i in range(s.resolution)]
		m = [y[i][2] for i in range(s.resolution)]
		h = [y[i][3] for i in range(s.resolution)]

		fq= fcy(s.timepoints, Vm, 0)
		print(ampl, fq)

		plt.close() 
		plt.subplot(2,1,1)
		plt.plot(s.timepoints,Vm)
		plt.subplot(2,1,2)
		plt.plot(s.timepoints, n, s.timepoints, m , s.timepoints, h)
		plt.show(False)

		# f = fft.fft(Vm[251:] - np.mean(Vm[251:]))
		# freq = fft.fftfreq(len(f))
		# rec.append(np.abs(len(Vm[251:]) * 1e4 / s.resolution * freq[np.argmax(np.abs(f))]))

		rec.append(fq)

	plt.close() 
	# plt.plot(s.timepoints,Vm)
	plt.plot(np.linspace(valmin, valmax,valres), rec) 
	plt.show()

	# plt.subplot(2,1,1)
	# plt.plot(freq*100000, f)

	# plt.subplot(2,1,2)
	# plt.plot(np.linspace(0,100,10000),Vm)

	# plt.show()