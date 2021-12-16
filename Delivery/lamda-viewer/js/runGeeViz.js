showMessage('Loading',staticTemplates.loadingModal);
var getDate = function(name,jd_split_string = '_jd'){
  var yr = name.split(jd_split_string)[0]
  yr = parseInt(yr.slice(yr.length-4,yr.length))
  var day = parseInt(name.split(jd_split_string)[1].split('-')[0])
  
  var d = ee.Date.fromYMD(yr,1,1).advance(day-1,'day')
  return d.millis()
 }
 function joinCollections(c1,c2, maskAnyNullValues){
  if(maskAnyNullValues === undefined || maskAnyNullValues === null){maskAnyNullValues = true}

  var MergeBands = function(element) {
    // A function to merge the bands together.
    // After a join, results are in 'primary' and 'secondary' properties.
    return ee.Image.cat(element.get('primary'), element.get('secondary'));
  };

  var join = ee.Join.inner();
  var filter = ee.Filter.equals('system:time_start', null, 'system:time_start');
  var joined = ee.ImageCollection(join.apply(c1, c2, filter));

  joined = ee.ImageCollection(joined.map(MergeBands));
  if(maskAnyNullValues){
    joined = joined.map(function(img){return img.mask(img.mask().and(img.reduce(ee.Reducer.min()).neq(0)))});
  }
  return joined;
}
function runGeeViz(){

	var bucketName = 'lamda-products';
	var study_areas = ['CONUS','AK'];
	var output_types = ['Z','TDD'];
	var output_type_stretch = {'Z':{'scale_factor':1000,
									'stretch' : -2.5*-2
									},
								'TDD':{'scale_factor':10000,
									'stretch' : -0.05*-2
									}
							}

	

				$.ajax({
			        type: 'GET',
			        url: `https://storage.googleapis.com/storage/v1/b/${bucketName}/o`,
			    }).done(function(json){
			    		
			    	var continuous_palette_chastain = ['a83800','ff5500','e0e0e0','a4ff73','38a800'];
		        json = json.items;
			        var names = json.map(nm => nm.name)
			        names = names.filter(nm => nm.indexOf('.tif')==nm.length-4)
			        
			        study_areas.map(function(study_area){
			        	var joined;
			        	output_types.map(function(output_type){

			        		var eight_bit_viz = {'min':0,'max':254,'palette':continuous_palette_chastain,'dateFormat':'YYYYMMdd','advanceInterval':'day'};
							var raw_viz = {'min':output_type_stretch[output_type]['stretch']*-1,'max':output_type_stretch[output_type]['stretch'],'palette':continuous_palette_chastain,'dateFormat':'YYYYMMdd','advanceInterval':'day'};
							
							var persistence_viz = {'min':0,'max':3,'palette':'e1e1e1,ffaa00,e10000,e100c5','dateFormat':'YYYYMMdd','advanceInterval':'day','classLegendDict':{'0 Detections':'e1e1e1','1 Detection':'ffaa00','2 Detections':'e10000','3 or More Detections':'e100c5'}};

							var persistence_viz = {'min':1,'max':3,'palette':'ffaa00,e10000,e100c5','dateFormat':'YYYYMMdd','advanceInterval':'day','classLegendDict':{'1 Detection':'ffaa00','2 Detections':'e10000','3 or More Detections':'e100c5'}};
			        		var namesT = names.filter(n => n.indexOf(study_area)== 0)
			        		namesT = namesT.filter(n => n.indexOf(output_type) > -1)
			        		
			        		var eight_bits= namesT.filter(i => i.indexOf('_8bit')>-1)
						    var persistence = namesT.filter(i => i.indexOf('_persistence')>-1)
						    var raws = namesT.filter(i => i.indexOf('_8bit')==-1 && i.indexOf('_persistence')==-1)
			        		

						    var raw_c = raws.map(function(t){
			        			var img = ee.Image.loadGeoTIFF(`gs://${bucketName}/${t}`).divide(output_type_stretch[output_type]['scale_factor'])
			        			img = img.set('system:time_start',getDate(t))
			        			return img
			        		})
			        		raw_c = ee.ImageCollection.fromImages(raw_c).select([0],[`LAMDA ${output_type}`])
			        		if(joined == undefined){
			        			joined = raw_c;
			        		}else{
			        			joined = joinCollections(joined,raw_c)
			        		}

						    Map2.addTimeLapse(raw_c, raw_viz,`${study_area} ${output_type} raw`)
						    

			       //  		var eight_bit_c = eight_bits.map(function(t){
			       //  			var img = ee.Image.loadGeoTIFF(`gs://${bucketName}/${t}`)
			       //  			img = img.set('system:time_start',getDate(t))
			       //  			return img
			       //  		})
			       //  		eight_bit_c = ee.ImageCollection.fromImages(eight_bit_c)
			        		
						    // Map2.addTimeLapse(eight_bit_c, eight_bit_viz,`${study_area} ${output_type} 8 bit`)
						    
						    var persistence_c = persistence.map(function(t){
			        			var img = ee.Image.loadGeoTIFF(`gs://${bucketName}/${t}`)
			        			img = img.selfMask()
			        			img = img.set('system:time_start',getDate(t,'_jds'))
			        			return img
			        		})
			        		persistence_c = ee.ImageCollection.fromImages(persistence_c)
			        		
						    Map2.addTimeLapse(persistence_c,persistence_viz,`${study_area} ${output_type} persistence`)
						    
			        	})
			        	pixelChartCollections[`${study_area}-pixel-charting`] =  {
						          'label':`${study_area} Time Series`,
						          'collection':joined,
						          'xAxisLabel':'Date',
						          'tooltip':'Query LAMDA raw time series',
						          'chartColors':['a83800','ff5500'],
						          'semiSimpleDate':true
						      };
			        })
			        populatePixelChartDropdown();
			        // setTimeout(function(){$('#close-modal-button').click();$('#CONUS-Z-8-bit-timelapse-1-name-span').click()}, 2500);

			    })

}
//