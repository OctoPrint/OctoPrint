/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/21/12
 * Time: 7:45 AM
 */

var GCODE = {};

GCODE.ui = (function(){
    var reader;
    var myCodeMirror;
    var sliderVer;
    var sliderHor;
    var gCodeLines = {first: 0, last: 0};
    var showGCode = false;

    var setProgress = function(id, progress){
        $('#'+id).width(parseInt(progress)+'%');
        $('#'+id).text(parseInt(progress)+'%');

    };

    var chooseAccordion = function(id){
//        debugger;
        $('#'+id).collapse("show");
    };

    var setLinesColor = function(toggle){
//        var i=0;
//        for(i=gCodeLines.first;i<gCodeLines.last; i++){
//            if(toggle){
//                myCodeMirror.setLineClass(Number(i), null, "activeline");
//            }else{
//                myCodeMirror.setLineClass(Number(i), null, null);
//            }
//        }
    }


    var printLayerInfo = function(layerNum){
        var z = GCODE.renderer.getZ(layerNum);
        var segments = GCODE.renderer.getLayerNumSegments(layerNum);
        var filament = GCODE.gCodeReader.getLayerFilament(z);
        var layerSpeeds = GCODE.gCodeReader.getModelInfo().speedsByLayer;
        var renderOptions = GCODE.renderer.getOptions();
        var colors = renderOptions["colorLine"];
        var speedIndex = 0;
        var keys, type;
        var showMove=false;
        var i = 0;
        var output = [];
        output.push("Layer number: " + layerNum);
        output.push("Layer height (mm): " + z);
        output.push("GCODE commands in layer: " + segments);
        output.push("Filament used by layer (mm): " + filament.toFixed(2));
        output.push("Print time for layer: " + parseFloat(GCODE.gCodeReader.getModelInfo().printTimeByLayer[z]).toFixed(1) + "sec");
        output.push("Extrude speeds:");
        for(i=0;i<layerSpeeds['extrude'][z].length;i++){
            if(typeof(layerSpeeds['extrude'][z][i])==='undefined'){continue;}
            speedIndex = i;
            if(speedIndex > colors.length -1){speedIndex = speedIndex % (colors.length-1);}
            output.push("<div id='colorBox"+i+"' class='colorBox' style='background-color: "+colors[speedIndex] + "'></div>  = " + (parseFloat(layerSpeeds['extrude'][z][i])/60).toFixed(2)+"mm/s");
        }
        if(typeof(layerSpeeds['move'][z]) !== 'undefined'){
            output.push("Move speeds:");
            for(i=0;i<layerSpeeds['move'][z].length;i++){
                if(typeof(layerSpeeds['move'][z][i])==='undefined'){continue;}
                speedIndex = i;
                if(speedIndex > colors.length -1){speedIndex = speedIndex % (colors.length-1);}
                output.push("<div id='colorBox"+i+"' class='colorBox' style='background-color: "+renderOptions['colorMove'] + "'></div>  = " + (parseFloat(layerSpeeds['move'][z][i])/60).toFixed(2)+"mm/s");
            }
        }
        if(typeof(layerSpeeds['retract'][z]) !== 'undefined'){
            output.push("Retract speeds:");
            for(i=0;i<layerSpeeds['retract'][z].length;i++){
                if(typeof(layerSpeeds['retract'][z][i])==='undefined'){continue;}
                speedIndex = i;
                if(speedIndex > colors.length -1){speedIndex = speedIndex % (colors.length-1);}
                output.push("<span style='color: " + renderOptions['colorRetract'] +"'>&#9679;</span> <span style='color: " + renderOptions['colorRestart'] +"'>&#9679;</span> = " +(parseFloat(layerSpeeds['retract'][z][i])/60).toFixed(2)+"mm/s");
            }
        }

        $('#layerInfo').html(output.join('<br>'));
//        chooseAccordion('layerAccordionTab');
    };

    var handleFileSelect = function(evt) {
//        console.log("handleFileSelect");
        evt.stopPropagation();
        evt.preventDefault();

        var files = evt.dataTransfer?evt.dataTransfer.files:evt.target.files; // FileList object.

        var output = [];
        for (var i = 0, f; f = files[i]; i++) {
            if(f.name.toLowerCase().match(/^.*\.(?:gcode|g|txt)$/)){
                output.push('<li>File extensions suggests GCODE</li>');
            }else{
                output.push('<li><strong>You should only upload *.gcode files! I will not work with this one!</strong></li>');
                document.getElementById('errorList').innerHTML = '<ul>' + output.join('') + '</ul>';
                return;
            }

            reader = new FileReader();
            reader.onload = function(theFile){
                chooseAccordion('progressAccordionTab');
                setProgress('loadProgress', 0);
                setProgress('analyzeProgress', 0);
//                myCodeMirror.setValue(theFile.target.result);
                GCODE.gCodeReader.loadFile(theFile);
                if(showGCode){
                    myCodeMirror.setValue(theFile.target.result);
                }else{
                    myCodeMirror.setValue("GCode view is disabled. You can enable it in 'GCode analyzer options' section.")
                }

            };
            reader.readAsText(f);
        }
    };

    var handleDragOver = function(evt) {
        evt.stopPropagation();
        evt.preventDefault();
        evt.target.dropEffect = 'copy'; // Explicitly show this is a copy.
    };

    var initSliders = function(){
        var prevX=0;
        var prevY=0;
        var handle;
        sliderVer =  $( "#slider-vertical" );
        sliderHor = $( "#slider-horizontal" );

        var onLayerChange = function(val){
            var progress = GCODE.renderer.getLayerNumSegments(val)-1;
            GCODE.renderer.render(val,0, progress);
            sliderHor.slider({max: progress, values: [0,progress]});
            setLinesColor(false); //clear current selection
            gCodeLines = GCODE.gCodeReader.getGCodeLines(val, sliderHor.slider("values",0), sliderHor.slider("values",1));
            setLinesColor(true); // highlight lines
            printLayerInfo(val);
        };

        sliderVer.slider({
            orientation: "vertical",
            range: "min",
            min: 0,
            max: GCODE.renderer.getModelNumLayers()-1,
            value: 0,
            slide: function( event, ui ) {
                onLayerChange(ui.value);
            }
        });

        //this stops slider reacting to arrow keys, since we do it below manually
        $( "#slider-vertical .ui-slider-handle" ).unbind('keydown');

        sliderHor.slider({
            orientation: "horizontal",
            range: "min",
            min: 0,
            max: GCODE.renderer.getLayerNumSegments(0)-1,
            values: [0,GCODE.renderer.getLayerNumSegments(0)-1],
            slide: function( event, ui ) {
                setLinesColor(false); //clear current selection
                gCodeLines = GCODE.gCodeReader.getGCodeLines(sliderVer.slider("value"),ui.values[0], ui.values[1]);
                setLinesColor(true); // highlight lines
                GCODE.renderer.render(sliderVer.slider("value"), ui.values[0], ui.values[1]);
            }
        });

        window.onkeydown = function (event){
            if(event.keyCode === 38 || event.keyCode === 33){
                if(sliderVer.slider('value') < sliderVer.slider('option', 'max')){
                    sliderVer.slider('value', sliderVer.slider('value')+1);
                    onLayerChange(sliderVer.slider('value'));
                }
            }else if(event.keyCode === 40 || event.keyCode === 34){
                if(sliderVer.slider('value') > 0){
                    sliderVer.slider('value', sliderVer.slider('value')-1);
                    onLayerChange(sliderVer.slider('value'));
                }
            }
            event.stopPropagation()
        }
    };

    var processMessage = function(e){
        var data = e.data;
        switch (data.cmd) {
            case 'returnModel':
                setProgress('loadProgress', 100);
                worker.postMessage({
                        "cmd":"analyzeModel",
                        "msg":{
                        }
                    }
                );
                break;
            case 'analyzeDone':
                var resultSet = [];

                setProgress('analyzeProgress',100);
                GCODE.gCodeReader.processAnalyzeModelDone(data.msg);
                GCODE.gCodeReader.passDataToRenderer();
                initSliders();
                resultSet.push("Model size is: " + data.msg.modelSize.x.toFixed(2) + 'x' + data.msg.modelSize.y.toFixed(2) + 'x' + data.msg.modelSize.z.toFixed(2)+'mm<br>');
                resultSet.push("Total filament used: " + data.msg.totalFilament.toFixed(2) + "mm<br>");
                resultSet.push("Estimated print time: " + parseInt(parseFloat(data.msg.printTime)/60/60) + ":" + parseInt((parseFloat(data.msg.printTime)/60)%60) + ":" + parseInt(parseFloat(data.msg.printTime)%60) + "<br>");
                resultSet.push("Estimated layer height: " + data.msg.layerHeight.toFixed(2) + "mm<br>");
                resultSet.push("Layer count: " + data.msg.layerCnt.toFixed(0) + "printed, " + data.msg.layerTotal.toFixed(0) + 'visited<br>');
                document.getElementById('list').innerHTML =  resultSet.join('');
                chooseAccordion('infoAccordionTab');
                $('#myTab a[href="#tab2d"]').tab('show');
                break;
            case 'returnLayer':
                GCODE.gCodeReader.processLayerFromWorker(data.msg);
                setProgress('loadProgress',data.msg.progress);
                break;
            case 'returnMultiLayer':
                GCODE.gCodeReader.processMultiLayerFromWorker(data.msg);
                setProgress('loadProgress',data.msg.progress);
                break;
            case "analyzeProgress":
                setProgress('analyzeProgress',data.msg.progress);
                break;
            default:
                console.log("default msg received" + data.cmd);
        }
    };

    var checkCapabilities = function(){
        var warnings = [];
        var fatal = [];

        Modernizr.addTest('filereader', function () {
            return !!(window.File && window.FileList && window.FileReader);
        });

        if(!Modernizr.canvas)fatal.push("<li>Your browser doesn't seem to support HTML5 Canvas, this application won't work without it.</li>");
        //if(!Modernizr.filereader)fatal.push("<li>Your browser doesn't seem to support HTML5 File API, this application won't work without it.</li>");
        if(!Modernizr.webworkers)fatal.push("<li>Your browser doesn't seem to support HTML5 Web Workers, this application won't work without it.</li>");
        if(!Modernizr.svg)fatal.push("<li>Your browser doesn't seem to support HTML5 SVG, this application won't work without it.</li>");

        if(fatal.length>0){
            document.getElementById('errorList').innerHTML = '<ul>' + fatal.join('') + '</ul>';
            console.log("Initialization failed: unsupported browser.")
            return false;
        }

        if(!Modernizr.webgl && GCODE.renderer3d){
            warnings.push("<li>Your browser doesn't seem to support HTML5 Web GL, 3d mode is not recommended, going to be SLOW!</li>");
            GCODE.renderer3d.setOption({rendererType: "canvas"});
        }
        if(!Modernizr.draganddrop)warnings.push("<li>Your browser doesn't seem to support HTML5 Drag'n'Drop, Drop area will not work.</li>");

        if(warnings.length>0){
            document.getElementById('errorList').innerHTML = '<ul>' + wanings.join('') + '</ul>';
            console.log("Initialization succeeded with warnings.")
        }
        return true;
    };


    return {
        worker: undefined,
        initHandlers: function(){
            var capabilitiesResult = checkCapabilities();
            if(!capabilitiesResult){
                return;
            }

            setProgress('loadProgress', 0);
            setProgress('analyzeProgress', 0);

            worker = new Worker('static/gcodeviewer/js/Worker.js');

            worker.addEventListener('message', processMessage, false);

            GCODE.ui.processOptions();
            GCODE.renderer.render(0,0);

            console.log("Application initialized");

        },

        ArrayIndexOf: function(a, fnc) {
            if (!fnc || typeof (fnc) != 'function') {
                return -1;
            }
            if (!a || !a.length || a.length < 1) return -1;
            for (var i = 0; i < a.length; i++) {
                if(!a[i]) continue;
                if (fnc(a[i])) return i;
            }
            return -1;
        },
        updateLayerInfo: function(layerNum){
          printLayerInfo(layerNum);
        },

        processOptions: function(){
            if(document.getElementById('sortLayersCheckbox').checked)GCODE.gCodeReader.setOption({sortLayers: true});
            else GCODE.gCodeReader.setOption({sortLayers: false});

            if(document.getElementById('purgeEmptyLayersCheckbox').checked)GCODE.gCodeReader.setOption({purgeEmptyLayers: true});
            else GCODE.gCodeReader.setOption({purgeEmptyLayers: false});

            if(document.getElementById('showGCodeCheckbox').checked)showGCode = true;
            else showGCode = false;


//            if(document.getElementById('sortLayersCheckbox').checked) worker.postMessage({"cmd":"setOption", "msg":{sortLayers: true}});
//            else  worker.postMessage({"cmd":"setOption", "msg":{sortLayers: false}});
//
//            if(document.getElementById('purgeEmptyLayersCheckbox').checked)worker.postMessage({"cmd":"setOption", "msg":{purgeEmptyLayers: true}});
//            else worker.postMessage({"cmd":"setOption", "msg":{purgeEmptyLayers: false}});

//            if(document.getElementById('analyzeModelCheckbox').checked)worker.postMessage({"cmd":"setOption", "msg":{analyzeModel: true}});
//            else worker.postMessage({"cmd":"setOption", "msg":{analyzeModel: false}});


            if(document.getElementById('moveModelCheckbox').checked)GCODE.renderer.setOption({moveModel: true});
            else GCODE.renderer.setOption({moveModel: false});

            if(document.getElementById('showMovesCheckbox').checked)GCODE.renderer.setOption({showMoves: true});
            else GCODE.renderer.setOption({showMoves: false});

            if(document.getElementById('showRetractsCheckbox').checked)GCODE.renderer.setOption({showRetracts: true});
            else GCODE.renderer.setOption({showRetracts: false});

            if(document.getElementById('differentiateColorsCheckbox').checked)GCODE.renderer.setOption({differentiateColors: true});
            else GCODE.renderer.setOption({differentiateColors: false});

            var widthMod = 2;
            if(Number($('#widthModifier').attr('value'))) {widthMod = Number($('#widthModifier').attr('value'));}
            if(document.getElementById('thickExtrusionCheckbox').checked)GCODE.renderer.setOption({extrusionWidth: widthMod});
            else GCODE.renderer.setOption({extrusionWidth: 1});

            if(document.getElementById('showNextLayer').checked)GCODE.renderer.setOption({showNextLayer: true});
            else GCODE.renderer.setOption({showNextLayer: false});
        }
    }
}());