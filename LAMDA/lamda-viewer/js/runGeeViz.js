showMessage('Loading',staticTemplates.loadingModal);
var getDate = function(name,jd_split_string = '_jd'){
  var yr = name.split(jd_split_string)[0]
  yr = parseInt(yr.slice(yr.length-4,yr.length))
  var day = parseInt(name.split(jd_split_string)[1].split('-')[0])
  
  var d = ee.Date.fromYMD(yr,1,1).advance(day-1,'day')
  return d.millis()
 }
function runGeeViz(){

	var bucketName = 'lamda-products';
	var study_areas = ['CONUS','AK'];
	var output_types = ['Z','TDD'];


	

				$.ajax({
			        type: 'GET',
			        url: `https://storage.googleapis.com/storage/v1/b/${bucketName}/o`,
			    }).done(function(json){
			    		
			    	var continuous_palette_chastain = ['a83800','ff5500','e0e0e0','a4ff73','38a800'];
		        json = json.items
			        var names = json.map(nm => nm.name)
			        names = names.filter(nm => nm.indexOf('.tif')==nm.length-4)
			        
			        study_areas.map(function(study_area){
			        	output_types.map(function(output_type){

			        		var eight_bit_viz = {'min':0,'max':254,'palette':continuous_palette_chastain,'dateFormat':'YYYYMMdd','advanceInterval':'day'};
	
							var persistence_viz = {'min':0,'max':3,'palette':'e1e1e1,ffaa00,e10000,e100c5','dateFormat':'YYYYMMdd','advanceInterval':'day','classLegendDict':{'0 Detections':'e1e1e1','1 Detection':'ffaa00','2 Detections':'e10000','3 Detections':'e100c5'}};

			        		var namesT = names.filter(n => n.indexOf(study_area)== 0)
			        		namesT = namesT.filter(n => n.indexOf(output_type) > -1)
			        		
			        		var eight_bits= namesT.filter(i => i.indexOf('_8bit')>-1)
						    var persistence = namesT.filter(i => i.indexOf('_persistence')>-1)
						    var raws = namesT.filter(i => i.indexOf('_8bit')==-1 && i.indexOf('_persistence')==-1)
			        		

			        		var eight_bit_c = eight_bits.map(function(t){
			        			var img = ee.Image.loadGeoTIFF(`gs://${bucketName}/${t}`)
			        			img = img.set('system:time_start',getDate(t))
			        			return img
			        		})
			        		eight_bit_c = ee.ImageCollection.fromImages(eight_bit_c)
			        		
						    Map2.addTimeLapse(eight_bit_c, eight_bit_viz,`${study_area} ${output_type} 8 bit`)
						    
						    var persistence_c = persistence.map(function(t){
			        			var img = ee.Image.loadGeoTIFF(`gs://${bucketName}/${t}`)
			        			img = img.set('system:time_start',getDate(t,'_jds'))
			        			return img
			        		})
			        		persistence_c = ee.ImageCollection.fromImages(persistence_c)
			        		
						    Map2.addTimeLapse(persistence_c,persistence_viz,`${study_area} ${output_type} persistence`)
						    
			        	})
			        })
			        // setTimeout(function(){$('#close-modal-button').click();$('#CONUS-Z-8-bit-timelapse-1-name-span').click()}, 2500);

			    })

}
//