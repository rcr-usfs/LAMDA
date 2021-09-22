"""
	 Copyright 2021 Ian Housman, RedCastle Resources Inc.

	 Licensed under the Apache License, Version 2.0 (the "License");
	 you may not use this file except in compliance with the License.
	 You may obtain a copy of the License at

			 http://www.apache.org/licenses/LICENSE-2.0

	 Unless required by applicable law or agreed to in writing, software
	 distributed under the License is distributed on an "AS IS" BASIS,
	 WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
	 See the License for the specific language governing permissions and
	 limitations under the License.
"""
#Script to support the LAndscape Monitoring and Detection Application (LAMDA) for local post-procesing
####################################################################################################
from osgeo import gdal
from osgeo import gdal_array
from osgeo import osr, ogr
from osgeo import gdalconst
import numpy,os
####################################################################################################
#Method for updating projection, no data, and stats of image and ensuring output is a valid COGtif
#Cog methods adapted from: https://geoexamples.com/other/2019/02/08/cog-tutorial.html/
def update_cog(image,crs,no_data_value = -9999, update_stats = True, stat_stretch_type = 'stdDev',stretch_n_stdDev = 4):
	print('Updating crs and no data and preserving COG layout for: ',image)
	cog_image = '{}_cog{}'.format(os.path.splitext(image)[0],os.path.splitext(image)[1])

	#Update projection, no data, and stats
	set_projection(image,crs)
	set_no_data(image, no_data_value, update_stats, stat_stretch_type,stretch_n_stdDev )

	#Set up COGtif bits that likely got broken when updating the projection etc
	rast = gdal.Open(image, gdal.GA_Update)
	rast.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64])
	driver = gdal.GetDriverByName('GTiff')
	ds2 = driver.CreateCopy(cog_image, rast,
									options=["COPY_SRC_OVERVIEWS=YES",
									"TILED=YES",
									"COMPRESS=DEFLATE"])
	rast = None
	ds2 = None

	#Remove the old file and rename the temp cog file
	os.remove(image)
	os.rename(cog_image,image)
####################################################################################################
#Function to set the projection of a raster
#This does not reproject the image, but merely updates the projection in the header
def set_projection(image,crs):
	rast = gdal.Open(image, gdal.GA_Update)
	rast.SetProjection(crs)
	rast = None
####################################################################################################
#Set the no data and then update stats
#If stat_stretch_type isn't set to stdDev, min-max will be used
def set_no_data(image, no_data_value = -9999, update_stats = True, stat_stretch_type = 'stdDev',stretch_n_stdDev = 4):
	rast = gdal.Open(image, gdal.GA_Update)
		
	b = rast.GetRasterBand(1)
	b.SetNoDataValue(no_data_value)
	if update_stats:
		Min,Max,Mean,Std = b.ComputeStatistics(0)
		if stat_stretch_type == 'stdDev':
			Min = Mean - (stretch_n_stdDev*Std)
			Max = Mean + (stretch_n_stdDev*Std)
		b.SetStatistics(Min,Max,Mean,Std)

		print(('Min:',Min))
		print(('Max:',Max))
		print(('Mean:',Mean))
		print(('Std:', Std))
	rast = None
	b = None
####################################################################################################
#Function to take an image, apply a stretch to it to convert it to 8 bit, add a color ramp, and names
def rescale(array,in_min,in_max,out_min = 0,out_max = 254):
	return ((array.clip(in_min,in_max) - in_min) * (out_max - out_min)) /  (in_max - in_min)
format_dict =  {'.tif': 'GTiff', '.img' : 'HFA', '.jpg' : 'JPEG', '.gif' : 'GIF', '.grid' : 'AAIGrid', '.hdr': 'envi', '': 'envi','.ntf': 'NITF','.vrt':'VRT'}
####################################################################################################
#Options found at: https://gdal.org/python/osgeo.gdal-module.html#TranslateOptions
cogArgs = {'format':'COG','creationOptions':['COMPRESS=DEFLATE']}
def translate(input,output,kwargs = {
    'rgbExpand':'rgb',
    'widthPct':6.25,
    'heightPct':6.25
	}):
	
	if 'format' not in kwargs.keys():
		kwargs['format'] = format_dict[os.path.splitext(output)[1]]
	

	print('Running gdal_translate:',output)
	ds = gdal.Translate(output, input, **kwargs)
	# do something with ds if you need
	ds = None # close and save ds

####################################################################################################
#Function to take raw image and rescale it to 8 bit, set no data, update stats, and set a colormap and names
#This method ensures output is a valid COGtif
#Cog methods adapted from: https://geoexamples.com/other/2019/02/08/cog-tutorial.html/
def stretch_to_8bit(in_image,in_no_data,scale_factor,stretch,palette,out_min = 0,out_max = 254,out_no_data = 255):
	#Set up a unique output name
	out_image = os.path.splitext(in_image)[0] + '_{}_8bit.tif'.format(stretch)


	if  not os.path.exists(out_image):
		print('Compressing {} to 8 bit'.format(in_image))

		#Read in raster as array
		rast = gdal.Open(in_image)
		width = rast.RasterXSize
		height = rast.RasterYSize

		band1 = rast.GetRasterBand(1)
		band1_pixels = band1.ReadAsArray().astype('float32')
		
		band1 = None
		
		#Apply stretch
		out = rescale(band1_pixels/scale_factor,-stretch,stretch,out_min,out_max)

		#Burn in mask values
		out[band1_pixels == in_no_data] = out_no_data

		#Write out output as a cogTif
		try:
			driver = gdal.GetDriverByName('MEM')
			ds = driver.Create('', width, height, 1, gdal.GDT_Byte)
			ds.SetProjection(rast.GetProjection())
			ds.SetGeoTransform(rast.GetGeoTransform())
		

			b = ds.GetRasterBand(1)
			b.WriteArray(out)
			b.SetNoDataValue(out_no_data)
			# if update_stats:
			# 	Min,Max,Mean,Std = b.ComputeStatistics(0)
			# 	if stat_stretch_type == 'stdDev':
			# 		Min = Mean - (stretch_n_stdDev*Std)
			# 		Max = Mean + (stretch_n_stdDev*Std)
			b.SetStatistics(out_min,out_max,125,20)


			ct = get_poly_gradient_ct(palette, out_min,out_max)
			names = ["{:.4f}".format(((i/(out_max-out_min))*(stretch+stretch))-stretch) for i in range(out_min,out_max+1)]
			names.append('No Data')
			b.SetRasterColorTable(ct)
			b.SetRasterCategoryNames(names)

			ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64])

			driver = gdal.GetDriverByName('GTiff')
			ds2 = driver.CreateCopy(out_image, ds,
									options=["COPY_SRC_OVERVIEWS=YES",
									"TILED=YES",
									"COMPRESS=DEFLATE"])
	
		except Exception as e:
			print(e)
		
		rast = None
		band1_pixels = None
		out = None
		ds = None
		ds2 = None
		b = None

		# #Update no data and stats
		# set_no_data(out_image, out_no_data,update_stats = True, stat_stretch_type = 'asdf')
		# #Update color table and names of 8 bit image
		# ct = get_poly_gradient_ct(palette, out_min,out_max)
		# names = ["{:.4f}".format(((i/(out_max-out_min))*(stretch+stretch))-stretch) for i in range(out_min,out_max+1)]
		# names.append('No Data')
		# # print(stretch,names)
		# update_color_table_or_names(out_image,color_table = ct,names = names)

		out_jpg = os.path.splitext(out_image)[0]+ '.jpg'
		translate(out_image,out_jpg)
####################################################################################################
#Compute persistence for RTFD outputs
#This method ensures output is a valid COGtif
#Cog methods adapted from: https://geoexamples.com/other/2019/02/08/cog-tutorial.html/
def calc_persistence(inputs,output_name,scale_factor,thresh,in_no_data = -32768,out_no_data = 255):

	#Read in rasters 
	stack = []
	for in_image in inputs:
		print('Reading in:',in_image)
		rast = gdal.Open(in_image)
		

		band1 = rast.GetRasterBand(1)
		stack.append(band1.ReadAsArray().astype('float32'))

		band1 = None
	stack = numpy.array(stack)

	#Set up output mask (union of all masked values)(must have non null values for all n periods for persistence)
	msk = numpy.max(stack == in_no_data,0)

	#Convert array based on scale factor
	stack= stack/scale_factor

	#Threshold output and get count and apply mask
	change = stack < thresh
	count = numpy.sum(change,0)
	count[msk] = out_no_data


	#Write out output as a COGtif
	try:
		
		driver = gdal.GetDriverByName('MEM')
		ds = driver.Create('', count.shape[1], count.shape[0], 1, gdal.GDT_Byte)
		ds.SetProjection(rast.GetProjection())
		ds.SetGeoTransform(rast.GetGeoTransform())
		

		b = ds.GetRasterBand(1)
		b.WriteArray(count)
		b.SetNoDataValue(out_no_data)
		# if update_stats:
		# 	Min,Max,Mean,Std = b.ComputeStatistics(0)
		# 	if stat_stretch_type == 'stdDev':
		# 		Min = Mean - (stretch_n_stdDev*Std)
		# 		Max = Mean + (stretch_n_stdDev*Std)
		# b.SetStatistics(out_min,out_max,125,20)


		#Update colors and names
		ct = gdal.ColorTable()

		ct.SetColorEntry(0,(225,225,225))#hex_to_rgb('#888888'))
		ct.SetColorEntry(1,(255,170,0))#hex_to_rgb('#888800'))
		ct.SetColorEntry(2,(225,0,0))#hex_to_rgb('#880000'))
		ct.SetColorEntry(3,(225,0,197))#hex_to_rgb('#880088'))

		names = ['{} Detection(s)'.format(i) for i in range(0,4)]
		b.SetRasterColorTable(ct)
		b.SetRasterCategoryNames(names)

		ds.BuildOverviews("NEAREST", [2, 4, 8, 16, 32, 64])

		driver = gdal.GetDriverByName('GTiff')
		ds2 = driver.CreateCopy(output_name, ds,
									options=["COPY_SRC_OVERVIEWS=YES",
									"TILED=YES",
									"COMPRESS=DEFLATE"])
	
	except Exception as e:
		print(e)
		
	rast = None
	count = None
	out = None
	ds = None
	ds2 = None
	b = None


	# #Update no data and stats
	# set_no_data(output_name, out_no_data,update_stats = True, stat_stretch_type = 'asdf')

	# #Update colors and names
	# ct = gdal.ColorTable()

	# ct.SetColorEntry(0,(225,225,225))#hex_to_rgb('#888888'))
	# ct.SetColorEntry(1,(255,170,0))#hex_to_rgb('#888800'))
	# ct.SetColorEntry(2,(225,0,0))#hex_to_rgb('#880000'))
	# ct.SetColorEntry(3,(225,0,197))#hex_to_rgb('#880088'))

	# names = ['{} Detection(s)'.format(i) for i in range(0,4)]
	# update_color_table_or_names(output_name,color_table = ct,names = names)

	out_jpg = os.path.splitext(output_name)[0]+ '.jpg'
	translate(output_name,out_jpg)
##############################################################
def color_dict_maker(gradient):
	''' Takes in a list of RGB sub-lists and returns dictionary of
		colors in RGB and hex form for use in a graphing function
		defined later on '''
	return {"hex":[RGB_to_hex(RGB) for RGB in gradient],
			"r":[RGB[0] for RGB in gradient],
			"g":[RGB[1] for RGB in gradient],
			"b":[RGB[2] for RGB in gradient]}
##############################################################
def linear_gradient(start_hex, finish_hex="#FFFFFF", n=10):
	''' returns a gradient list of (n) colors between
		two hex colors. start_hex and finish_hex
		should be the full six-digit color string,
		inlcuding the number sign ("#FFFFFF") '''
	# Starting and ending colors in RGB form
	s = hex_to_rgb(start_hex)
	f = hex_to_rgb(finish_hex)
	# Initilize a list of the output colors with the starting color
	RGB_list = [s]
	# Calcuate a color at each evenly spaced value of t from 1 to n
	for t in range(1, n):
		# Interpolate RGB vector for color at the current value of t
		curr_vector = [
			int(s[j] + (float(t)/(n-1))*(f[j]-s[j]))
			for j in range(3)
		]
		# Add it to our list of output colors
		RGB_list.append(curr_vector)

	# print(RGB_list)
	return color_dict_maker(RGB_list)

def polylinear_gradient(colors, n):
	''' returns a list of colors forming linear gradients between
			all sequential pairs of colors. "n" specifies the total
			number of desired output colors '''
	# The number of colors per individual linear gradient
	n_out = int(float(n) / (len(colors) - 1)) + 1
	# print(('n',n))
	# print(('n_out',n_out))
	# If we don't have an even number of color values, we will remove equally spaced values at the end.
	apply_offset = False
	if n%n_out != 0:
		apply_offset = True
		n_out = n_out + 1
		# print(('new n_out',n_out))

	# returns dictionary defined by color_dict()
	gradient_dict = linear_gradient(colors[0], colors[1], n_out)

	if len(colors) > 1:
		for col in range(1, len(colors) - 1):
			next = linear_gradient(colors[col], colors[col+1], n_out)
			for k in ("hex", "r", "g", "b"):
				# Exclude first point to avoid duplicates
				gradient_dict[k] += next[k][1:]
	
	# Remove equally spaced values here.
	if apply_offset:
		#indList = list(range(len(gradient_dict['hex'])))
		offset = len(gradient_dict['hex'])-n
		sliceval = []
		# print(('len(gradient_dict)',len(gradient_dict['hex'])))
		# print(('offset',offset))
		
		for i in range(1, offset+1):
				sliceval.append(int(len(gradient_dict['hex'])*i/float(offset+2)))
		# print(('sliceval',sliceval))
		for k in ("hex", "r", "g", "b"):
				gradient_dict[k] = [i for j, i in enumerate(gradient_dict[k]) if j not in sliceval] 
		# print(('new len dict', len(gradient_dict['hex'])))
	return gradient_dict
def get_poly_gradient_ct(palette,min,max):
	ramp = polylinear_gradient(palette, max-min+1)
	paletteT= list(zip(ramp['r'],ramp['g'],ramp['b'],[255]*len(ramp['b'])))
	ct = gdal.ColorTable()
	
	for i, p in enumerate(range(min,max+1)):ct.SetColorEntry(p,paletteT[i])
	return ct

##############################################################
# color functions adapted from bsou.io/posts/color-gradients-with-python
def hex_to_rgb(value):
		"""Return (red, green, blue) for the color given as #rrggbb."""
		value = value.lstrip('#')
		lv = len(value)
		return tuple(int(value[i:i + lv // 3], 16) for i in range(0, lv, lv // 3))
def RGB_to_hex(RGB):
	''' [255,255,255] -> "#FFFFFF" '''
	# Components need to be integers for hex to make sense
	RGB = [int(x) for x in RGB]
	return "#"+"".join(["0{0:x}".format(v) if v < 16 else
						"{0:x}".format(v) for v in RGB])

##############################################################
#Function to get a gdal color table with a provided set of hex colors
def get_ct(colors):
	palette = [hex_to_rgb(i)+(255,) for i in colors]
	ct = gdal.ColorTable()
	i = 0
	for color in palette:
		ct.SetColorEntry(i,color)
		i+=1
	return ct
#Function to set the color table and names
def update_color_table_or_names(image,color_table = '',names = ''):
		rast = gdal.Open(image, gdal.GA_Update)
		b = rast.GetRasterBand(1)
		if color_table != '' and color_table != None:
				print(('Updating color table for:',image))
				b.SetRasterColorTable(color_table)
			 
		if names != '' and names != None:
				print(('Updating names for:',image))
				b.SetRasterCategoryNames(names)
		rast = None
		b = None
############################################################### 
