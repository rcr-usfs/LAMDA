//https://storage.googleapis.com/storage/v1/b/rtfd-scratch/o
var analysisYears = [2020];

var nDays = 16;

var startJulians = ee.List.sequence(65,321,8).getInfo();

var zBaselineLength = 3;

var baselineGap = 1;

var epochLength = 5;

//Persistence params
var slopeThresh = -0.05;
var zThresh = -2.5;
var persistencePeriod = 3;
var persistenceReducer = ee.Reducer.percentile([100]);

var indexName = 'NBR';

var runName = 'CONUS_Test';

var bucket = 'gs://rtfd-scratch';

var exportArea = ee.FeatureCollection('projects/lcms-292214/assets/CONUS-Ancillary-Data/conus');

var lossDurPalette = 'FF0,F00,ff00c3';//'0C2780,E2F400,BD1600';
var lossMagPalette = 'D00,F5DEB3';
///////////////////////////////////////////////////////////////////////
analysisYears.map(function(ay){
  var ts = [];
  startJulians.map(function(startJulian){
    var endJulian = startJulian + nDays-1;
    var date = ee.Date.fromYMD(ay,1,1).advance(startJulian,'day');
    // indexNames.map(function(indexName){
      
      var baselineStartYear = ay-baselineGap-zBaselineLength;
	    var baselineEndYear = ay-baselineGap -1;
	    
	    var tddStartYear =  ay-epochLength+1;
	    var tddEndYear = ay;
	    
	    var nameZ = 'bl'+baselineStartYear.toString() + '-'+baselineEndYear.toString()+
      '_ay'+ay.toString() + 
      '_jd'+startJulian.toString() + '-'+endJulian.toString();
      var urlZ = bucket + '/' +runName + '_RTFD_Z_'+indexName+ '_'+nameZ
       + '.tif';
      
      var nameTDD = 'yrs'+ tddStartYear.toString() + '-' + tddEndYear.toString() + 
      '_jd'+startJulian.toString() + '-'+endJulian.toString();
      var urlTDD = bucket + '/' +runName + '_RTFD_TDD_'+indexName+ '_'+nameTDD
       + '.tif';
      
      var imgZ = ee.Image.loadGeoTIFF(urlZ);
      imgZ = imgZ.updateMask(imgZ.neq(-32768)).divide(1000).clip(exportArea);
      Map.addLayer(imgZ,{min:-3,max:3,palette:'F00,888,00F'},'Z '+nameZ,false);
      
      var imgTDD = ee.Image.loadGeoTIFF(urlTDD);
      imgTDD = imgTDD.updateMask(imgTDD.neq(-32768)).divide(100000).clip(exportArea);
      Map.addLayer(imgTDD,{min:-0.05,max:0.05,palette:'F00,888,00F'},'TDD '+nameTDD,false);
      
      ts.push(ee.Image.cat([imgZ,imgTDD]).rename(['z','tdd']).float().set(
        {'system:time_start':date.millis(),
        'startJulian':startJulian,
        'endJulian':endJulian
        }));
      
      if(ts.length >= persistencePeriod){
        var tst = ee.ImageCollection(ts.slice(ts.length-persistencePeriod,ts.length));
        
        var change = tst.map(function(img){return img.lte(ee.Image([zThresh,slopeThresh])).selfMask()});
        var changeCount = change.count();
        var changeMag = tst.reduce(persistenceReducer).updateMask(changeCount.mask());
        Map.addLayer(changeCount.select([0]),{min:1,max:persistencePeriod,palette:lossDurPalette},'Z Persistence Count '+startJulian.toString() + '-'+endJulian.toString(),false);
        Map.addLayer(changeMag.select([0]),{min:-4,max:-1,palette:lossMagPalette},'Z Persistence Mag '+startJulian.toString() + '-'+endJulian.toString(),false);
        Map.addLayer(changeCount.select([1]),{min:1,max:persistencePeriod,palette:lossDurPalette},'TDD Persistence Count '+startJulian.toString() + '-'+endJulian.toString(),false);
        Map.addLayer(changeMag.select([1]),{min:-0.1,max:-0.02,palette:lossMagPalette},'TDD Persistence Mag '+startJulian.toString() + '-'+endJulian.toString(),false)
      }
      // print(ts.length)
    });
  // });
  ts = ee.ImageCollection(ts);
  Map.addLayer(ts,{},'time series',false);
});



Map.setOptions('HYBRID');