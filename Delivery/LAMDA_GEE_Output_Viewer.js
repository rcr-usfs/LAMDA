var app = {};

//-------- Map Panel-----------------
app.map = ui.Map();
app.map.style().set({cursor:'crosshair'});
app.map.setOptions('HYBRID');

app.optionsFiltersPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {width: '250px', position: 'top-left'}
});
app.plotPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {width: '400',position:'top-right'}
});
app.ZdownloadPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {width: '225px',margin:'5px',border : '1px solid black'}
});
app.TDDdownloadPanel = ui.Panel({
  layout: ui.Panel.Layout.flow('vertical'),
  style: {width: '225',margin:'5px',border : '1px solid black'}
});
app.legendPanel = ui.Panel(null, null, {position: 'bottom-right',margin:'5px'});
app.chartPanel = ui.Panel(null, null, {stretch: 'horizontal'});
app.blackline = function(){return ui.Label('__________________________________________')};
app.wideBlackline = function(){return ui.Label('____________________________________________________________________________')};

//https://storage.googleapis.com/storage/v1/b/rtfd-scratch/o
var analysisYears = [2020];

var nDays = 16;

var startJulians = ee.List.sequence(209,233,8).getInfo();//ee.List.sequence(65,321,8).getInfo();

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
      var storageAPIUrlZ= urlZ.replace('gs:/','https://storage.googleapis.com');
      var storageAPIUrlTDD= urlTDD.replace('gs:/','https://storage.googleapis.com');
      app.ZdownloadPanel.add(ui.Label('RTFD Z '+ay.toString() + ' '+startJulian.toString() + '-'+endJulian.toString(), null, storageAPIUrlZ));
      app.TDDdownloadPanel.add(ui.Label('RTFD TDD '+tddStartYear.toString() + '-' + tddEndYear.toString() + ' '+startJulian.toString() + '-'+endJulian.toString(),null,storageAPIUrlTDD));
      // app.ZdownloadPanel.add(app.blackline());
      var imgZ = ee.Image.loadGeoTIFF(urlZ);
      imgZ = imgZ.updateMask(imgZ.neq(-32768)).divide(1000).clip(exportArea);
      app.map.addLayer(imgZ,{min:-3,max:3,palette:'F00,888,00F'},'Z '+nameZ,false);
      
      var imgTDD = ee.Image.loadGeoTIFF(urlTDD);
      imgTDD = imgTDD.updateMask(imgTDD.neq(-32768)).divide(100000).clip(exportArea);
      app.map.addLayer(imgTDD,{min:-0.05,max:0.05,palette:'F00,888,00F'},'TDD '+nameTDD,false);
      
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
        app.map.addLayer(changeCount.select([0]),{min:1,max:persistencePeriod,palette:lossDurPalette},'Z Persistence Count '+startJulian.toString() + '-'+endJulian.toString(),false);
        app.map.addLayer(changeMag.select([0]),{min:-4,max:-1,palette:lossMagPalette},'Z Persistence Mag '+startJulian.toString() + '-'+endJulian.toString(),false);
        app.map.addLayer(changeCount.select([1]),{min:1,max:persistencePeriod,palette:lossDurPalette},'TDD Persistence Count '+startJulian.toString() + '-'+endJulian.toString(),false);
        app.map.addLayer(changeMag.select([1]),{min:-0.1,max:-0.02,palette:lossMagPalette},'TDD Persistence Mag '+startJulian.toString() + '-'+endJulian.toString(),false)
      }
      // print(ts.length)
    });
  // });
  ts = ee.ImageCollection(ts);
  Map.addLayer(ts,{},'time series',false);
});


// app.downloadSelect = ui.Select(app.downloadList,'Select Output to Download',null,app.downloadSelectedOutput)
app.ZdownloadPanelShown = false;
app.TDDdownloadPanelShown = false;
app.togglePanel = function(containerID,panelID,panelShown,index){
  if(panelShown){
    containerID.remove(panelID);
    panelShown = false;
  }else{
    containerID.insert(index,panelID);
    panelShown = true;
  }
  return panelShown;
};
app.toggleZDownloadPanel = function(){
  app.ZdownloadPanelShown =app.togglePanel(app.optionsFiltersPanel,app.ZdownloadPanel,app.ZdownloadPanelShown,2);
};
app.toggleTDDDownloadPanel = function(){
  app.TDDdownloadPanelShown =app.togglePanel(app.optionsFiltersPanel,app.TDDdownloadPanel,app.TDDdownloadPanelShown,3);
};
app.toggleZDownloadPanelButton = ui.Button('Toggle RTFD Z Downloads',app.toggleZDownloadPanel,false,{padding:'0px',margin:'5px',fontSize:'5px',position:'top-left'});
app.toggleTDDDownloadPanelButton = ui.Button('Toggle RTFD TDD Downloads',app.toggleTDDDownloadPanel,false,{padding:'0px',margin:'5px',fontSize:'5px',position:'top-left'});
app.optionsFiltersPanel.add(app.toggleZDownloadPanelButton);
app.optionsFiltersPanel.add(app.toggleTDDDownloadPanelButton);
// app.optionsFiltersPanel.add(app.ZdownloadPanel);
// app.optionsFiltersPanel.add(app.TDDdownloadPanel);
// print(app.downloadList)
/////////////////////////////////////////////////////////////

app.filtersShown = true;
app.plotsShown = true;
app.hideFilters = function(){
  ui.root.remove(app.optionsFiltersPanel);
  app.toggleFiltersButton.setLabel('-->');
  app.filtersShown = false;
};
app.showFilters = function(){
  ui.root.insert(0,app.optionsFiltersPanel);
  app.toggleFiltersButton.setLabel('<--');
  app.filtersShown = true;
};
app.toggleFilters = function(){
  if(app.filtersShown){
    app.hideFilters();
  }else{app.showFilters()}
}

app.hidePlotPanel = function(){
  ui.root.remove(app.plotPanel);
  app.togglePlotPanelButton.setLabel('<--');
  app.plotsShown = false;
};
app.showPlotPanel = function(){
  ui.root.insert(2,app.plotPanel);
  app.togglePlotPanelButton.setLabel('-->');
  app.plotsShown = true;
};
app.togglePlotPanel = function(){
  if(app.plotsShown){
    app.hidePlotPanel();
  }else{app.showPlotPanel()}
};
app.toggleFiltersButton = ui.Button('<--',app.toggleFilters,false,{padding:'0px',margin:'0px',fontSize:'5px',position:'top-left'});
app.togglePlotPanelButton = ui.Button('-->',app.togglePlotPanel,false,{padding:'0px',margin:'0px',fontSize:'5px',position:'top-right'});

app.map.add(app.toggleFiltersButton);
app.map.add(app.togglePlotPanelButton);

/////////////////////////////////////////////////////////////
app.plotPanel.add(app.wideBlackline());
//Put app together
ui.root.clear();
ui.root.add(app.optionsFiltersPanel);

ui.root.add(app.map);
ui.root.add(app.plotPanel);