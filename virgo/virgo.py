import os
import sys
import argparse
import time
import numpy as np
import math
import datetime
import shutil
import warnings

def simulate(l, b, beamwidth=0.6, v_min=-400, v_max=400, plot_file=''):
	'''
	Simulate 21 cm profiles based on the LAB HI Survey.
	
	Args:
		l: float. Target galactic longitude [deg]
		b: float. Target galactic latitude [deg]
		beamwidth: float. Telescope half-power beamwidth (approx. equal to 0.7 * lambda/D) [deg]
		v_min: float. Minimum radial velocity (xlim) [km/s]
		v_max: float. Maximum radial velocity (xlim) [km/s]
		plot_file: string. Output plot filename
	'''
	import requests
	import matplotlib
	import matplotlib.pyplot as plt

	if plot_file != '':
		plt.rcParams['figure.figsize'] = (9,7)
	plt.rcParams['legend.fontsize'] = 14
	plt.rcParams['axes.labelsize'] = 14
	plt.rcParams['axes.titlesize'] = 16
	plt.rcParams['xtick.labelsize'] = 12
	plt.rcParams['ytick.labelsize'] = 12

	# Establish velocity limits
	if v_min < -400:
		v_min = -400
	if v_max > 400:
		v_max = 400

	# Download LAB Survey HI data
	try:
		response = requests.get('https://www.astro.uni-bonn.de/hisurvey/euhou/LABprofile/download.php?ral='+str(l)+'&decb='+str(b)+'&csys=0&beam='+str(beamwidth))
	except requests.exceptions.ConnectionError:
		raise requests.exceptions.ConnectionError('Failed to reach astro.uni-bonn.de. Make sure you are connected to the internet and try again.')

	data = response.content

	# Parse data
	data = data.splitlines()
	data = data[4:]
	#data = [' '.join(line.split()).replace('\n', '') for line in data]

	frequency = []
	spectrum = []
	for line in data:
		try:
			frequency.append(float(line.split()[2]))
			spectrum.append(float(line.split()[1]))
		except IndexError:
			break

	# Convert km/s to m/s
	v_min = v_min*1000
	v_max = v_max*1000

	# Define Frequency limits
	left_frequency_edge = 1420.4057517667 + 1420.4057517667e6 * -v_max/(299792458 * 1e6)
	right_frequency_edge = 1420.4057517667 + 1420.4057517667e6 * -v_min/(299792458 * 1e6)

	# Limit galactic coordinates to 2 decimal places
	l = float('%.2f' % l)
	b = float('%.2f' % b)

	# Initiate plot
	fig, ax = plt.subplots()

	try:
		plt.title('Simulated HI Profile $(l$=$'+str(l)+'\degree$, $b$=$'+str(b)+'\degree)$ | Beamwidth: $'+str(beamwidth)+'\degree$', pad=40)
	except: # Catch missing TeX exception
		plt.title('Simulated HI Profile (l='+str(l)+' deg, b='+str(b)+' deg) | Beamwidth: '+str(beamwidth)+' deg', pad=40)

	# Plot data
	ax.plot(frequency, spectrum, label='LAB Survey')
	ax.set_xlabel('Frequency (MHz)')
	ax.set_ylabel('Brightness Temperature (K)')
	ax.set_xlim(left_frequency_edge, right_frequency_edge)
	ax.ticklabel_format(useOffset=False)
	ax.legend(loc='upper left')

	# Set secondary axis for Radial Velocity
	ax_secondary = ax.twiny()
	ax_secondary.set_xlabel('Radial Velocity (km/s)', labelpad=5)
	ax_secondary.axvline(x=0, color='brown', linestyle='--', linewidth=2, zorder=0)

	ax_secondary.set_xlim(v_max/1000, v_min/1000)
	ax_secondary.tick_params(axis='x', direction='in', pad=2)
	ax.grid()

	if plot_file != '':
		# Save plot to file
		plt.savefig(plot_file, bbox_inches='tight', pad_inches=0.1)
	else:
		# Display plot
		plt.show()
	plt.clf()
	plt.close()

def predict(lat, lon, height=0, source='', date='', plot_sun=True, plot_file=''):
	'''
	Plots source Alt/Az given the observer's Earth coordinates.
	
	Args:
		lat: float. Observer latitude [deg]
		lon: float. Obesrver longitude [deg]
		height: float. Observer elevation [m]
		source: string. Source name
		date: string. Date in YYYY-MM-DD format. If no date is given, it defaults to today's system date.
		plot_sun: bool. Also plot Sun position for reference
		plot_file: string. Output plot filename
	'''
	from astropy.time import Time
	from astropy.visualization import astropy_mpl_style, quantity_support
	from astropy.coordinates import SkyCoord, EarthLocation, AltAz, get_sun
	import astropy.units as u
	import matplotlib
	import matplotlib.pyplot as plt

	plt.style.use(astropy_mpl_style)
	plt.rcParams['figure.constrained_layout.use'] = True
	plt.rcParams['figure.figsize'] = (18,10)
	plt.rcParams['legend.fontsize'] = 20
	plt.rcParams['axes.labelsize'] = 22
	plt.rcParams['axes.titlesize'] = 26
	plt.rcParams['xtick.labelsize'] = 18
	plt.rcParams['ytick.labelsize'] = 18

	quantity_support()

	# Define source
	if source != '':
		obj = SkyCoord.from_name(source)

	# Set observer location
	loc = EarthLocation(lat=lat*u.deg, lon=lon*u.deg, height=height*u.m)

	# Get system timezone and set UTC offset
	try:
		offset = time.timezone if (time.localtime().tm_isdst == 0) else time.altzone
		utcoffset = (offset / 60 / 60 * -1) * u.hour
	except:
		utcoffset = 0

	# Fetch toady's system date if not specified
	if date == '':
		date = datetime.datetime.today().strftime('%Y-%m-%d')

	midnight = Time(date+' 00:00:00') - utcoffset
	delta_midnight = np.linspace(0, 24, 1000)*u.hour
	full_day = midnight + delta_midnight
	frame = AltAz(obstime=full_day, location=loc)
	sun_altaz = get_sun(full_day).transform_to(frame)

	if source != '':
		obj_altaz = obj.transform_to(frame)

	# Note source altitude peak
	if source != '':
		seconds = float(delta_midnight[np.argmax(obj_altaz.alt*u.deg)]*3600/u.hour)
		max = seconds/3600

		plt.axvline(x=max, color='brown', linestyle='--', linewidth=2, zorder=2)

		# Plot source
		plt.scatter(delta_midnight, obj_altaz.alt,
					c=obj_altaz.az, label=source, lw=0, s=8,
					cmap='viridis')

	# Plot Sun
	if plot_sun:
		plt.scatter(delta_midnight, sun_altaz.alt,
					c=sun_altaz.az, label='Sun', lw=0, s=8,
					cmap='viridis')

	# Plot properties
	plt.colorbar(aspect=40).set_label('Azimuth (deg)', labelpad=13)
	plt.legend(loc='best')

	plt.xlim(0*u.hour, 24*u.hour)
	plt.xticks((np.arange(24))*u.hour)
	plt.ylim(0*u.deg, 90*u.deg)

	if source != '':
		plt.title(source+' | '+date, y=1.01)
	else:
		plt.title('Sun | '+date, y=1.01)

	offset = ["", "+"][int(utcoffset/u.hour) > 0] + str(int(utcoffset/u.hour))
	if utcoffset/u.hour != 0:
		plt.xlabel('Time (UTC'+str(offset)+')')
	else:
		plt.xlabel('Time (UTC)')
	plt.ylabel('Altitude')

	if plot_file != '':
		plt.savefig(plot_file, bbox_inches='tight', pad_inches=0.2)
	else:
		plt.show()
	plt.clf()

def equatorial(alt, az, lat, lon, height=0):
	'''
	Takes observer's location and Alt/Az as input and returns RA/Dec as a tuple.
	
	Args:
		alt: float. Altitude [deg]
		az: float. Azimuth [deg]
		lat: float. Observer latitude [deg]
		lon: float. Observer longitude [deg]
		height: float. Observer elevation [m]
	'''
	from astropy.time import Time
	from astropy.coordinates import SkyCoord, EarthLocation, AltAz
	import astropy.units as u

	# Set observer location
	loc = EarthLocation(lat=lat * u.deg, lon=lon * u.deg, height=height * u.m)

	# Get current system time
	current_time = Time.now()

	# Compute Alt/Az
	AltAzcoordiantes = SkyCoord(alt=alt * u.deg, az=az * u.deg,
				    obstime=current_time, frame='altaz', location=loc)

	# Transform to RA/Dec
	c = AltAzcoordiantes.icrs

	ra = c.ra.hour
	dec = c.dec.deg

	# Return position as tuple
	return (ra, dec)

def galactic(ra, dec):
	'''
	Converts RA/Dec. to galactic coordinates, returning galactic longitude and latitude (tuple).
	
	Args:
		ra: float. Right ascension [hr]
		dec: float. Declination [deg]
	'''
	from astropy.time import Time
	from astropy.coordinates import SkyCoord, EarthLocation, AltAz
	import astropy.units as u

	# Transform source position to galactic longitude & latitude
	equatorial = SkyCoord(ra=ra * u.hour, dec=dec * u.deg, frame='icrs')
	galactic = equatorial.galactic

	l = galactic.l.deg
	b = galactic.b.deg

	# Return position as tuple
	return (l, b)

def frequency(wavelength):
	'''
	Transform wavelength to frequency.
	
	Args:
		wavelength: float. Wavelength [m]
	'''
	# Define speed of light
	c = 299792458.0

	# Compute and return frequency (Hz)
	f = c/wavelength

	return f

def wavelength(frequency):
	'''
	Transform frequency to wavelength.
	
	Args:
		frequency: float. Wave frequency [Hz]
	'''
	# Define speed of light
	c = 299792458.0

	# Compute and return wavelength (m)
	l = c/frequency

	return l

def gain(D, f, e=0.7, u='dBi'):
	'''
	Estimate parabolic antenna gain.
	
	Args:
		D: float. Antenna diameter [m]
		f: float. Frequency [Hz]
		e: float. Aperture efficiency (0 >= e >= 1)
		u: string. Output gain unit ('dBi', 'linear' or 'K/Jy')
	'''
	# Compute antenna gain of parabolic antenna
	G_ant = e*(math.pi*D/wavelength(f))**2

	if u.lower() == 'lin' or u.lower() == 'linear':
		# Gain unit: linear
		return G_ant
	elif u.lower() == 'db' or u.lower() == 'dbi':
		# Gain unit: dBi
		G_ant = 10*np.log10(G_ant)

		return G_ant
	else:
		# Gain unit: K/Jy
		A_eff = (G_ant*wavelength(f)**2)/(4*math.pi)

		# Define Boltzmann constant
		k_B = 1.38064852e-23

		# Transform gain to K/Jy
		G_ant = 1e-26 * A_eff/(2*1.38064852e-23)

		return G_ant

def A_e(gain, f):
	'''
	Transform antenna gain to effective aperture [m^2].
	
	Args:
		gain: float. Antenna gain [dBi]
		f: float. Frequency [Hz]
	'''
	# Compute and return effective antenna aperture (m^2)
	A_eff = (10**(gain/10)*wavelength(f)**2)/(4*math.pi)

	return A_eff

def beamwidth(D, f):
	'''
	Estimate parabolic antenna half-power beamwidth (FWHM).
	
	Args:
		D: float. Antenna diameter [m]
		f: float. Frequency [Hz]
	'''
	# Compute and return half-power beamwidth of a parabolic antenna
	hpbw = 70*wavelength(f)/D

	return hpbw

def NF(T_noise, T_ref=290):
	'''
	Convert noise temperature to noise figure [dB].
	
	Args:
		T_noise: float. Noise temperature [K]
		T_ref: float. Reference temperature [K]
	'''
	# Compute and return noise figure
	nf = 10*np.log10((T_noise/T_ref) + 1)

	return nf

def T_noise(NF, T_ref=290):
	'''
	Convert noise figure to noise temperature [K].
	
	Args:
		NF: float. Noise figure [dB]
		T_ref: float. Reference temperature [K]
	'''
	# Compute and return noise temperature
	T_noise = T_ref*((10**(NF/10)) - 1)

	return T_noise

def G_T(gain, T_sys):
	'''
	Compute antenna gain-to-noise-temperature (G/T).
	
	Args:
		gain: float. Antenna gain [dBi]
		T_sys: float. System noise temperature [K]
	'''
	# Compute and return antenna gain-to-noise-temperature (G/T)
	G_T = gain-10*np.log10(T_sys)

	return G_T

def SEFD(A_e, T_sys):
	'''
	Compute system equivalent flux density [Jy].
	
	Args:
		A_e: float. Effective antenna aperture [m^2]
		T_sys: float. System noise temperature [K]
	'''
	# Define Boltzmann constant
	k_B = 1.38064852e-23

	# Compute and return the system equivalent flux density (Jy)
	sefd = 10**26 * 2*k_B*T_sys/A_e

	return sefd

def snr(S, sefd, t, bw):
	'''
	Estimate the obtained signal-to-noise ratio of an observation (radiometer equation).
	
	Args:
		S: float. Source flux density [Jy]
		sefd: float. Instrument's system equivalent flux density [Jy]
		t: float. Total on-source integration time [sec]
		bw: float. Acquisition bandwidth [Hz]
	'''
	# Estimate and return the signal-to-noise ratio (radiometer equation)
	snr = S*math.sqrt(t*bw)/sefd

	return snr

def map_hi(ra=None, dec=None, plot_file=''):
	'''
	Plots the all-sky 21 cm map (LAB HI survey). Setting RA/Dec (optional args) will add a red dot indicating where the telescope is pointing to.
	
	Args:
		ra: float. Right ascension [hr]
		dec: float. Declination [deg]
		plot_file: string. Output plot filename
	'''
	import matplotlib
	import matplotlib.pyplot as plt

	# Adjust figsize
	if plot_file != '':
		plt.rcParams["figure.figsize"] = (20,20)

	# Get package path
	if sys.version_info >= (3, 4):
		import importlib.util
		virgo_path = importlib.util.find_spec('virgo').submodule_search_locations[0]
	else:
		import imp
		virgo_path = sys.modules['virgo'].__path__[0]

	# Load HI survey
	survey = np.loadtxt(virgo_path+'/map.txt')

	# Flip array to match RA and Dec axes
	survey_corrected = np.flip(survey, 1)

	# Plot map
	plt.imshow(survey_corrected, extent=[24,0,-90,90], aspect=0.07, interpolation='gaussian')

	# Plot properties
	plt.title('All-Sky Map (21 cm)', fontsize=28, y=1.01)
	plt.xticks(np.arange(0, 24.01, 2))
	plt.xlabel('Right Ascension (hours)', fontsize=20)
	plt.ylabel('Declination (deg)', fontsize=20)
	plt.xticks(fontsize=16)
	plt.yticks(fontsize=16)

	# Plot given source position
	if ra is not None and dec is not None:
		if ra >= 0 and ra <= 24 and dec >= -90 and dec <= 90:
			plt.axvline(ra, 0, 1, linestyle='--', linewidth=2, color=(0.85, 0.15, 0.16, 0.9))
			plt.axhline(dec, 0, 1, linestyle='--', linewidth=2, color=(0.85, 0.15, 0.16, 0.9))
			plt.scatter(ra, dec, s=200, color=[0.85, 0.15, 0.16])
		else:
			warnings.warn('RA and/or Dec out of range. Ensure the input is decimal hours and decimal degrees respectively.')

	if plot_file != '':
                # Add survey citation
                plt.text(5.62, 92.1, 'LAB HI Survey (Kalberla et al., 2005)', fontsize=14, bbox={'facecolor': 'white', 'pad': 4})

                # Save plot to file
                plt.savefig(plot_file, bbox_inches='tight')
	else:
		# Display plot
		plt.tight_layout()
		plt.show()
	plt.clf()

def observe(obs_parameters, spectrometer='wola', obs_file='observation.dat', start_in=0):
	'''
	Begin data acquisition (requires SDR connected to the machine).
	
	Args:
		obs_parameters: dict. Observation parameters
			dev_args: string. Device arguments (gr-osmosdr)
			rf_gain: float. RF gain
			if_gain: float. IF gain
			bb_gain: float. Baseband gain
			frequency: float. Center frequency [Hz]
			bandwidth: float. Instantaneous bandwidth [Hz]
			channels: int: Number of frequency channels (FFT size)
			t_sample: float: Integration time per FFT sample
			duration: float: Total observing duration [sec]
		spectrometer: string. Spectrometer flowchart/pipeline ('WOLA'/'FTF')
		obs_file: string. Output data filename
		start_in: float. Schedule observation start [sec]
	'''
	if spectrometer.lower() != 'wola':
		try:
			from run_ftf import run_observation
		except:
			from .run_ftf import run_observation
	else:
		try:
			from run_wola import run_observation
		except:
			from .run_wola import run_observation

	dev_args = obs_parameters['dev_args']
	rf_gain = obs_parameters['rf_gain']
	if_gain = obs_parameters['if_gain']
	bb_gain = obs_parameters['bb_gain']
	frequency = obs_parameters['frequency']
	bandwidth = obs_parameters['bandwidth']
	channels = obs_parameters['channels']
	t_sample = obs_parameters['t_sample']
	duration = obs_parameters['duration']

	# Schedule observation
	#if start_in != 0:
	#	print('[*] The observation will begin in '+str(start_in)+' sec automatically. Please wait...\n')

	time.sleep(start_in)

	# Delete pre-existing observation file
	try:
		os.remove(obs_file)
	except OSError:
		pass

	# Note current datetime
	epoch = time.time()

	# Convert timestamp to MJD
	mjd = epoch/86400.0 + 40587

	# Run observation
	#print('\n[+] Starting observation at ' + time.strftime('%Y-%m-%d %H:%M:%S %Z', time.localtime(epoch)) + '...\n')

	observation = run_observation(dev_args=dev_args, frequency=frequency, bandwidth=bandwidth, rf_gain=rf_gain,
                              if_gain=if_gain, bb_gain=bb_gain, channels=channels,
							  duration=duration, t_sample=t_sample, obs_file=obs_file)
	observation.start()
	observation.wait()

	#print('\n[+] Data acquisition complete. Observation saved as: '+obs_file)

	# Write observation parameters to header file
	with open('.'.join(obs_file.split('.')[:-1])+'.header', 'w') as f:
		f.write('''mjd='''+str(mjd)+'''
dev_args='''+str(dev_args)+'''
rf_gain='''+str(rf_gain)+'''
if_gain='''+str(if_gain)+'''
bb_gain='''+str(bb_gain)+'''
frequency='''+str(frequency)+'''
bandwidth='''+str(bandwidth)+'''
channels='''+str(channels)+'''
t_sample='''+str(t_sample)+'''
duration='''+str(duration))

def plot(obs_parameters='', n=0, m=0, f_rest=0, slope_correction=False, dB=False, rfi=[0,0], xlim=[0,0], ylim=[0,0], dm=0,
	 obs_file='observation.dat', cal_file='', waterfall_fits='', spectra_csv='', power_csv='', plot_file='plot.png'):
	'''
	Process, analyze and plot data.
	
	Args:
		obs_parameters: dict. Observation parameters (identical to parameters used to acquire data)
			dev_args: string. Device arguments (gr-osmosdr)
			rf_gain: float. RF gain
			if_gain: float. IF gain
			bb_gain: float. Baseband gain
			frequency: float. Center frequency [Hz]
			bandwidth: float. Instantaneous bandwidth [Hz]
			channels: int: Number of frequency channels (FFT size)
			t_sample: float: Integration time per FFT sample
			duration: float: Total observing duration [sec]
		n: int. Median filter factor (spectrum)
		m: int. Median filter factor (time series)
		f_rest: float. Spectral line reference frequency used for radial velocity (Doppler shift) calculations [Hz]
		slope_correction: bool. Correct slope in poorly-calibrated spectra using linear regression
		dB: bool. Display data in decibel scaling
		rfi: list. Blank frequency channels contaminated with RFI ([low_frequency, high_frequency]) [Hz]
		xlim: list. x-axis limits ([low_frequency, high_frequency]) [Hz]
		ylim: list. y-axis limits ([start_time, end_time]) [Hz]
		dm: float. Dispersion measure for dedispersion [pc/cm^3]
		obs_file: string. Input observation filename (generated with virgo.observe)
		cal_file: string. Input calibration filename (generated with virgo.observe)
		waterfall_fits: string. Output FITS filename
		spectra_csv: string. Output CSV filename (spectra)
		power_csv: string. Output CSV filename (time series)
		plot_file: string. Output plot filename
	'''
	import matplotlib
	matplotlib.use('Agg') # Try commenting this line if you run into display/rendering errors
	import matplotlib.pyplot as plt
	from matplotlib.gridspec import GridSpec

	plt.rcParams['legend.fontsize'] = 14
	plt.rcParams['axes.labelsize'] = 14
	plt.rcParams['axes.titlesize'] = 18
	plt.rcParams['xtick.labelsize'] = 12
	plt.rcParams['ytick.labelsize'] = 12

	def decibel(x):
		if dB: return 10.0*np.log10(x)
		return x

	def shift(phase_num, n_rows):
		waterfall[:, phase_num] = np.roll(waterfall[:, phase_num], -n_rows)

	def SNR(spectrum, mask=np.array([])):
		'''Signal-to-Noise Ratio estimator, with optional masking.
		If mask not given, then all channels will be used to estimate noise
		(will drastically underestimate S:N - not robust to outliers!)'''

		if mask.size == 0:
			mask = np.zeros_like(spectrum)

		noise = np.nanstd((spectrum[2:]-spectrum[:-2])[mask[1:-1] == 0])/np.sqrt(2)
		background = np.nanmean(spectrum[mask == 0])

		return (spectrum-background)/noise

	def best_fit(power):
		'''Compute best Gaussian fit'''
		avg = np.nanmean(power)
		var = np.var(power)

		gaussian_fit_x = np.linspace(np.min(power),np.max(power),100)
		gaussian_fit_y = 1.0/np.sqrt(2*np.pi*var)*np.exp(-0.5*(gaussian_fit_x-avg)**2/var)

		return [gaussian_fit_x, gaussian_fit_y]

	# Load observation parameters from dictionary argument/header file
	if obs_parameters != '':
		frequency = obs_parameters['frequency']
		bandwidth = obs_parameters['bandwidth']
		channels = obs_parameters['channels']
		t_sample = obs_parameters['t_sample']
	else:
		header_file = '.'.join(obs_file.split('.')[:-1])+'.header'

		warnings.warn('No observation parameters passed. Attempting to load from header file ('+header_file+')...')

		with open(header_file, 'r') as f:
			headers = [parameter.rstrip('\n') for parameter in f.readlines()]

		for i in range(len(headers)):
			if 'mjd' in headers[i]:
				mjd = float(headers[i].strip().split('=')[1])
			elif 'frequency' in headers[i]:
				frequency = float(headers[i].strip().split('=')[1])
			elif 'bandwidth' in headers[i]:
				bandwidth = float(headers[i].strip().split('=')[1])
			elif 'channels' in headers[i]:
				channels = int(headers[i].strip().split('=')[1])
			elif 't_sample' in headers[i]:
				t_sample = float(headers[i].strip().split('=')[1])

	# Transform frequency axis limits to MHz
	xlim = [x / 1e6 for x in xlim]

	# Define Radial Velocity axis limits
	left_velocity_edge = -299792.458*(bandwidth-2*frequency+2*f_rest)/(bandwidth-2*frequency)
	right_velocity_edge = 299792.458*(-bandwidth-2*frequency+2*f_rest)/(bandwidth+2*frequency)

	# Transform sampling time to number of bins
	bins = int(t_sample*bandwidth/channels)

	# Load observation & calibration data
	offset = 1
	waterfall = offset*np.fromfile(obs_file, dtype='float32').reshape(-1, channels)/bins

	# Delete first 3 rows (potentially containing outlier samples)
	waterfall = waterfall[3:, :]

	# Mask RFI-contaminated channels
	if rfi != [0,0]:
		# Frequency to channel transformation
		rfi_lo = channels*(rfi[0] - (frequency - bandwidth/2))/bandwidth
		rfi_hi = channels*(rfi[1] - (frequency - bandwidth/2))/bandwidth

		# Blank channels
		for i in range(int(rfi_lo), int(rfi_hi)):
			waterfall[:, i] = np.nan

	if cal_file != '':
		waterfall_cal = offset*np.fromfile(cal_file, dtype='float32').reshape(-1, channels)/bins

		# Delete first 3 rows (potentially containing outlier samples)
		waterfall_cal = waterfall_cal[3:, :]

		# Mask RFI-contaminated channels
		if rfi != [0,0]:
			# Blank channels
			for i in range(int(rfi_lo), int(rfi_hi)):
				waterfall_cal[:, i] = np.nan

	# Compute average spectra
	with warnings.catch_warnings():
		warnings.filterwarnings(action='ignore', message='Mean of empty slice')
		avg_spectrum = decibel(np.nanmean(waterfall, axis=0))
		if cal_file != '':
			avg_spectrum_cal = decibel(np.nanmean(waterfall_cal, axis=0))

	# Number of sub-integrations
	subs = waterfall.shape[0]

	# Compute Time axis
	t = t_sample*np.arange(subs)

	# Compute Frequency axis; convert Hz to MHz
	frequency = np.linspace(frequency-0.5*bandwidth, frequency+0.5*bandwidth,
	                        channels, endpoint=False)*1e-6

	# Perform de-dispersion
	if dm != 0:
		deltaF = float(np.max(frequency)-np.min(frequency))/subs
		f_start = np.min(frequency)
		for t_bin in range(subs):
			f_chan = f_start+t_bin*deltaF
			deltaT = 4149*dm*((1/(f_chan**2))-(1/(np.max(frequency)**2)))
			n = int((float(deltaT)/(float(1)/channels)))
			shift(t_bin, n)

	# Define array for Time Series plot
	power = decibel(np.nanmean(waterfall, axis=1))

	# Apply Mask
	mask = np.zeros_like(avg_spectrum)
	mask[np.logical_and(frequency > f_rest*1e-6-0.2, frequency < f_rest*1e-6+0.8)] = 1 # Margins OK for galactic HI

	# Define text offset for axvline text label
	text_offset = 0

	# Calibrate Spectrum
	if cal_file != '':
		if dB:
			spectrum = 10**((avg_spectrum-avg_spectrum_cal)/10)
		else:
			spectrum = avg_spectrum/avg_spectrum_cal

		spectrum = SNR(spectrum, mask)
		if slope_correction:
			idx = np.isfinite(frequency) & np.isfinite(spectrum)
			fit = np.polyfit(frequency[idx], spectrum[idx], 1)
			ang_coeff = fit[0]
			intercept = fit[1]
			fit_eq = ang_coeff*frequency + intercept
			spectrum = SNR(spectrum-fit_eq, mask)

		# Mitigate RFI (Frequency Domain)
		if n != 0:
			spectrum_clean = SNR(spectrum.copy(), mask)
			for i in range(0, int(channels)):
				spectrum_clean[i] = np.nanmedian(spectrum_clean[i:i+n])

		# Apply position offset for Spectral Line label
		text_offset = 60

	# Mitigate RFI (Time Domain)
	if m != 0:
		power_clean = power.copy()
		for i in range(0, int(subs)):
			power_clean[i] = np.nanmedian(power_clean[i:i+m])

	# Write Waterfall to file (FITS)
	if waterfall_fits != '':
		from astropy.io import fits

		# Load data
		hdu = fits.PrimaryHDU(waterfall)

		# Prepare FITS headers
		hdu.header['NAXIS'] = 2
		hdu.header['NAXIS1'] = channels
		hdu.header['NAXIS2'] = subs
		hdu.header['CRPIX1'] = channels/2
		hdu.header['CRPIX2'] = subs/2
		hdu.header['CRVAL1'] = frequency[int(channels/2)]
		hdu.header['CRVAL2'] = t[int(subs/2)]
		hdu.header['CDELT1'] = bandwidth*1e-6/channels
		hdu.header['CDELT2'] = t_sample
		hdu.header['CTYPE1'] = 'Frequency (MHz)'
		hdu.header['CTYPE2'] = 'Relative Time (s)'
		try:
			hdu.header['MJD-OBS'] = mjd
		except NameError:
			warnings.warn('Observation MJD could not be found and will not be part of the FITS header.')
			pass

		# Delete pre-existing FITS file
		try:
			os.remove(waterfall_fits)
		except OSError:
			pass

		# Write to file
		hdu.writeto(waterfall_fits)

	# Write Spectra to file (csv)
	if spectra_csv != '':
		if cal_file != '':
			np.savetxt(spectra_csv, np.concatenate((frequency.reshape(channels, 1),
                       avg_spectrum.reshape(channels, 1), avg_spectrum_cal.reshape(channels, 1),
                       spectrum.reshape(channels, 1)), axis=1), delimiter=',', fmt='%1.6f')
		else:
			np.savetxt(spectra_csv, np.concatenate((frequency.reshape(channels, 1),
                       avg_spectrum.reshape(channels, 1)), axis=1), delimiter=',', fmt='%1.6f')

	# Write Time Series to file (csv)
	if power_csv != '':
		np.savetxt(power_csv, np.concatenate((t.reshape(subs, 1), power.reshape(subs, 1)),
                   axis=1), delimiter=',', fmt='%1.6f')

	# Initialize plot
	if cal_file != '':
		fig = plt.figure(figsize=(27, 15))
		gs = GridSpec(2, 3)
	else:
		fig = plt.figure(figsize=(21, 15))
		gs = GridSpec(2, 2)

	# Plot Average Spectrum
	ax1 = fig.add_subplot(gs[0, 0])
	ax1.plot(frequency, avg_spectrum)
	if xlim == [0,0]:
		ax1.set_xlim(np.min(frequency), np.max(frequency))
	else:
		ax1.set_xlim(xlim[0], xlim[1])
	ax1.ticklabel_format(useOffset=False)
	ax1.set_xlabel('Frequency (MHz)')
	if dB:
		ax1.set_ylabel('Relative Power (dB)')
	else:
		ax1.set_ylabel('Relative Power')
	if f_rest != 0:
		ax1.set_title('Average Spectrum\n')
	else:
		ax1.set_title('Average Spectrum')
	ax1.grid()

	if xlim == [0,0] and f_rest != 0:
		# Add secondary axis for Radial Velocity
		ax1_secondary = ax1.twiny()
		ax1_secondary.set_xlabel('Radial Velocity (km/s)', labelpad=5)
		ax1_secondary.axvline(x=0, color='brown', linestyle='--', linewidth=2, zorder=0)
		ax1_secondary.annotate('Spectral Line\nRest Frequency', xy=(460-text_offset, 5),
                               xycoords='axes points', size=14, ha='left', va='bottom', color='brown')
		ax1_secondary.set_xlim(left_velocity_edge, right_velocity_edge)
		ax1_secondary.tick_params(axis='x', direction='in', pad=-22)

	#Plot Calibrated Spectrum
	if cal_file != '':
		ax2 = fig.add_subplot(gs[0, 1])
		ax2.plot(frequency, spectrum, label='Raw Spectrum')
		if n != 0:
			ax2.plot(frequency, spectrum_clean, color='orangered', label='Median (n = '+str(n)+')')
			ax2.set_ylim()
		if xlim == [0,0]:
			ax2.set_xlim(np.min(frequency), np.max(frequency))
		else:
			ax2.set_xlim(xlim[0], xlim[1])
		ax2.ticklabel_format(useOffset=False)
		ax2.set_xlabel('Frequency (MHz)')
		ax2.set_ylabel('Signal-to-Noise Ratio (S/N)')
		if f_rest != 0:
			ax2.set_title('Calibrated Spectrum\n')
		else:
			ax2.set_title('Calibrated Spectrum')
		if n != 0:
			if f_rest != 0:
				ax2.legend(bbox_to_anchor=(0.002, 0.96), loc='upper left')
			else:
				ax2.legend(loc='upper left')

		if xlim == [0,0] and f_rest != 0:
			# Add secondary axis for Radial Velocity
			ax2_secondary = ax2.twiny()
			ax2_secondary.set_xlabel('Radial Velocity (km/s)', labelpad=5)
			ax2_secondary.axvline(x=0, color='brown', linestyle='--', linewidth=2, zorder=0)
			ax2_secondary.annotate('Spectral Line\nRest Frequency', xy=(400, 5),
                                   xycoords='axes points', size=14, ha='left', va='bottom', color='brown')
			ax2_secondary.set_xlim(left_velocity_edge, right_velocity_edge)
			ax2_secondary.tick_params(axis='x', direction='in', pad=-22)
		ax2.grid()

	# Plot Dynamic Spectrum
	if cal_file != '':
		ax3 = fig.add_subplot(gs[0, 2])
	else:
		ax3 = fig.add_subplot(gs[0, 1])

	ax3.imshow(decibel(waterfall), origin='lower', interpolation='None', aspect='auto',
		   extent=[np.min(frequency), np.max(frequency), np.min(t), np.max(t)])
	if xlim == [0,0] and ylim != [0,0]:
		ax3.set_ylim(ylim[0], ylim[1])
	elif xlim != [0,0] and ylim == [0,0]:
		ax3.set_xlim(xlim[0], xlim[1])
	elif xlim != [0,0] and ylim != [0,0]:
		ax3.set_xlim(xlim[0], xlim[1])
		ax3.set_ylim(ylim[0], ylim[1])

	ax3.ticklabel_format(useOffset=False)
	ax3.set_xlabel('Frequency (MHz)')
	ax3.set_ylabel('Relative Time (s)')
	ax3.set_title('Dynamic Spectrum (Waterfall)')

	# Adjust Subplot Width Ratio
	if cal_file != '':
		gs = GridSpec(2, 3, width_ratios=[16.5, 1, 1])
	else:
		gs = GridSpec(2, 2, width_ratios=[7.6, 1])

	# Plot Time Series (Power vs Time)
	ax4 = fig.add_subplot(gs[1, 0])
	ax4.plot(t, power, label='Raw Time Series')
	if m != 0:
		ax4.plot(t, power_clean, color='orangered', label='Median (n = '+str(m)+')')
		ax4.set_ylim()
	if ylim == [0,0]:
		ax4.set_xlim(0, np.max(t))
	else:
		ax4.set_xlim(ylim[0], ylim[1])
	ax4.set_xlabel('Relative Time (s)')
	if dB:
		ax4.set_ylabel('Relative Power (dB)')
	else:
		ax4.set_ylabel('Relative Power')
	ax4.set_title('Average Power vs Time')
	if m != 0:
		ax4.legend(bbox_to_anchor=(1, 1), loc='upper right')
	ax4.grid()

	# Plot Total Power Distribution
	if cal_file != '':
		gs = GridSpec(2, 3, width_ratios=[7.83, 1.5, -0.325])
	else:
		gs = GridSpec(2, 2, width_ratios=[8.8, 1.5])

	ax5 = fig.add_subplot(gs[1, 1])

	ax5.hist(power, np.max([int(np.size(power)/50),10]), density=1, alpha=0.5, color='royalblue', orientation='horizontal', zorder=10)
	ax5.plot(best_fit(power)[1], best_fit(power)[0], '--', color='blue', label='Best fit (Raw)', zorder=20)
	if m != 0:
		ax5.hist(power_clean, np.max([int(np.size(power_clean)/50),10]), density=1, alpha=0.5, color='orangered', orientation='horizontal', zorder=10)
		ax5.plot(best_fit(power_clean)[1], best_fit(power_clean)[0], '--', color='red', label='Best fit (Median)', zorder=20)
	ax5.set_xlim()
	ax5.set_ylim()
	ax5.get_shared_x_axes().join(ax5, ax4)
	ax5.set_yticklabels([])
	ax5.set_xlabel('Probability Density')
	ax5.set_title('Total Power Distribution')
	ax5.legend(bbox_to_anchor=(1, 1), loc='upper right')
	ax5.grid()

	# Save plots to file
	plt.tight_layout()
	plt.savefig(plot_file)
	plt.clf()

def plot_rfi(rfi_parameters, data='rfi_data', dB=True, plot_file='plot.png'):
	'''
	Plots wideband RFI survey spectrum.
	
	Args:
		rfi_parameters: dict. Identical to obs_parameters, but also including 'f_lo': f_lo
		data: string. Survey data directory containing individual observations
		dB: bool. Display data in decibel scaling
		plot_file: string. Output plot filename
	'''
	import matplotlib
	matplotlib.use('Agg') # Try commenting this line if you run into display/rendering errors
	import matplotlib.pyplot as plt
	from matplotlib.gridspec import GridSpec

	plt.rcParams['legend.fontsize'] = 18
	plt.rcParams['axes.labelsize'] = 40
	plt.rcParams['axes.titlesize'] = 50
	plt.rcParams['xtick.labelsize'] = 34
	plt.rcParams['ytick.labelsize'] = 34

	f_lo = rfi_parameters['f_lo']
	bandwidth = rfi_parameters['bandwidth']
	channels = rfi_parameters['channels']
	t_sample = rfi_parameters['t_sample']
	duration = rfi_parameters['duration']

	def decibel(x):
		if dB: return 10.0*np.log10(x)
		return x

	# Transform sampling time to number of bins
	bins = int(t_sample*bandwidth/channels)

	offset = 1
	total = []

	# Count number of .dat files
	n = len([f for f in os.listdir(data) if f.endswith('.dat') and os.path.isfile(os.path.join(data, f))])

	for i in range(int(n)):
		# Load data
		waterfall = offset*np.fromfile(data+'/'+str(i)+'.dat', dtype='float32').reshape(-1, channels)/bins

		# Delete first 3 rows (potentially containing outlier samples)
		waterfall = waterfall[3:, :]

		total.append(waterfall)

	# Merge dynamic spectra
	combined = np.concatenate(total, axis=1)

	# Compute average spectra
	avg_spectrum = np.mean(combined, axis=0)

	# Compute frequency axis
	allfreq = []

	for i in range(int(n)):
		f_total = np.linspace((f_lo+bandwidth*i)-0.5*bandwidth, (f_lo+bandwidth*i)+0.5*bandwidth, channels, endpoint=False)*1e-6
		allfreq.append(f_total)

	f_total = np.concatenate(allfreq)

	# Initialize plot
	fig = plt.figure(figsize=(5*n,20.25))
	gs = GridSpec(1,1)

	# Plot merged spectra
	ax = fig.add_subplot(gs[0,0])

	ax.plot(f_total, decibel(avg_spectrum), '#3182bd')
	ax.set_ylim()
	ax.fill_between(f_total, decibel(avg_spectrum), y2=-1000, color='#deebf7')
	ax.set_xlim(np.min(f_total), np.max(f_total))
	ax.ticklabel_format(useOffset=False)
	ax.set_xlabel('Frequency (MHz)')

	if dB:
		ax.set_ylabel('Relative Power (dB)', x=-10)
	else:
		ax.set_ylabel('Relative Power', x=-10)

	ax.set_title('Average RFI Spectrum', y=1.0075)

	ax.annotate('Monitored frequency range: '+str(round(f_lo/1000000,1))+'-'+str(round(np.max(f_total),1))+' MHz ($\\Delta\\nu$ = '+str(round(((np.max(f_total)*1e6-f_lo)/1000000),1))+
' MHz)\nBandwidth per spectrum: '+str(bandwidth/1000000)+' MHz\nIntegration time per spectrum: '+str(duration)+' sec\nFFT size: '+str(channels), xy=(17, 1290),
xycoords='axes points', size=32, ha='left', va='top', color='brown')

	ax.grid()

	plt.tight_layout()
	plt.savefig(plot_file)
	plt.clf()

def monitor_rfi(f_lo, f_hi, obs_parameters, data='rfi_data'):
	'''
	Begin data acquisition (wideband RFI survey).
	
	Args:
		f_lo: float. Start frequency [Hz]
		f_hi: float. End frequency [Hz]
		obs_parameters: dict. Observation parameters (identical to parameters used to acquire data)
			dev_args: string. Device arguments (gr-osmosdr)
			rf_gain: float. RF gain
			if_gain: float. IF gain
			bb_gain: float. Baseband gain
			frequency: float. Center frequency [Hz]
			bandwidth: float. Instantaneous bandwidth [Hz]
			channels: int: Number of frequency channels (FFT size)
			t_sample: float: Integration time per FFT sample
			duration: float: Total observing duration [sec]
		data: string. Survey data directory to output individual observations to
	'''
	dev_args = obs_parameters['dev_args']
	rf_gain = obs_parameters['rf_gain']
	if_gain = obs_parameters['if_gain']
	bb_gain = obs_parameters['bb_gain']
	bandwidth = obs_parameters['bandwidth']
	channels = obs_parameters['channels']
	duration = obs_parameters['duration']

	t_sample = 0.1

	# Create RFI data directory
	if os.path.exists(data):
		shutil.rmtree(data)

	os.makedirs(data)

	# Iterate over the input frequency range
	i = 0
	for frequency in range(int(f_lo), int(f_hi), int(bandwidth)):
		rfi_parameters = {
			'dev_args': dev_args,
			'rf_gain': rf_gain,
			'if_gain': if_gain,
			'bb_gain': bb_gain,
			'frequency': frequency,
			'bandwidth': bandwidth,
			'channels': channels,
			't_sample': t_sample,
			'duration': duration,
			'f_lo': f_lo
		}

		# Run RFI monitor
		observe(obs_parameters=rfi_parameters, spectrometer='ftf', obs_file=data+'/'+str(i)+'.dat')
		i += 1

def main():
	# Load argument values
	parser = argparse.ArgumentParser()

	parser.add_argument('-da', '--dev_args', dest='dev_args',
                        help='SDR Device Arguments (osmocom Source)', type=str, default='')
	parser.add_argument('-rf', '--rf_gain', dest='rf_gain',
                        help='SDR RF Gain (dB)', type=float, default=10)
	parser.add_argument('-if', '--if_gain', dest='if_gain',
                        help='SDR IF Gain (dB)', type=float, default=20)
	parser.add_argument('-bb', '--bb_gain', dest='bb_gain',
                        help='SDR BB Gain (dB)', type=float, default=20)
	parser.add_argument('-f', '--frequency', dest='frequency',
                        help='Center Frequency (Hz)', type=float, required=True)
	parser.add_argument('-b', '--bandwidth', dest='bandwidth',
                        help='Bandwidth (Hz)', type=float, required=True)
	parser.add_argument('-c', '--channels', dest='channels',
                        help='Number of Channels (FFT Size)', type=int, required=True)
	parser.add_argument('-t', '--t_sample', dest='t_sample',
                        help='FFT Sample Time (s)', type=float, required=True)
	parser.add_argument('-d', '--duration', dest='duration',
                        help='Observing Duration (s)', type=float, default=60)
	parser.add_argument('-s', '--start_in', dest='start_in',
                        help='Schedule Observation (s)', type=float, default=0)
	parser.add_argument('-o', '--obs_file', dest='obs_file',
                        help='Observation Filename', type=str, default='observation.dat')
	parser.add_argument('-C', '--cal_file', dest='cal_file',
                        help='Calibration Filename', type=str, default='')
	parser.add_argument('-db', '--db', dest='dB',
                        help='Use dB-scaled Power values', default=False, action='store_true')
	parser.add_argument('-n', '--median_frequency', dest='n',
                        help='Median Factor (Frequency Domain)', type=int, default=0)
	parser.add_argument('-m', '--median_time', dest='m',
                        help='Median Factor (Time Domain)', type=int, default=0)
	parser.add_argument('-r', '--rest_frequency', dest='f_rest',
                        help='Spectral Line Rest Frequency (Hz)', type=float, default=0)
	parser.add_argument('-W', '--waterfall_fits', dest='waterfall_fits',
                        help='Filename for FITS Waterfall File', type=str, default='')
	parser.add_argument('-S', '--spectra_csv', dest='spectra_csv',
                        help='Filename for Spectra csv File', type=str, default='')
	parser.add_argument('-P', '--power_csv', dest='power_csv',
                        help='Filename for Spectra csv File', type=str, default='')
	parser.add_argument('-p', '--plot_file', dest='plot_file',
                        help='Plot Filename', type=str, default='plot.png')

	args = parser.parse_args()

	# Define data-acquisition parameters
	observation = {
	'dev_args': args.dev_args,
    'rf_gain': args.rf_gain,
    'if_gain': args.if_gain,
    'bb_gain': args.bb_gain,
    'frequency': args.frequency,
    'bandwidth': args.bandwidth,
    'channels': args.channels,
    't_sample': args.t_sample,
    'duration': args.duration
	}

	# Acquire data from SDR
	observe(obs_parameters=observation, obs_file=args.obs_file, start_in=args.start_in)

	# Plot data
	plot(obs_parameters=observation, n=args.n, m=args.m, f_rest=args.f_rest,
	     dB=args.dB, obs_file=args.obs_file, cal_file=args.cal_file, waterfall_fits=args.waterfall_fits,
		 spectra_csv=args.spectra_csv, power_csv=args.power_csv, plot_file=args.plot_file)

if __name__ == '__main__':
	main()
