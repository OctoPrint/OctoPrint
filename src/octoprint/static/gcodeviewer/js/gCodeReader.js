/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/21/12
 * Time: 7:31 AM
 */

GCODE.gCodeReader = (function(){
// ***** PRIVATE ******
    var gcode, lines;
    var z_heights = {};
    var model = [];
    var max = {x: undefined, y: undefined, z: undefined};
    var min = {x: undefined, y: undefined, z: undefined};
    var modelSize = {x: undefined, y: undefined, z: undefined};
    var filamentByLayer = {};
    var printTimeByLayer;
    var totalFilament=0;
    var printTime=0;
    var speeds = {};
    var speedsByLayer = {};
    var gCodeOptions = {
        sortLayers: false,
        purgeEmptyLayers: true,
        analyzeModel: false
    };

    var percentageTree = undefined;

    var prepareGCode = function(totalSize){
        if(!lines)return;
        gcode = [];
        var i, tmp, byteCount;

        byteCount = 0;
        for(i=0;i<lines.length;i++){
            byteCount += lines[i].length + 1; // line length + \n
            tmp = lines[i].indexOf(";");
            if(tmp > 1 || tmp === -1) {
                gcode.push({line: lines[i], percentage: byteCount * 100 / totalSize});
            }
        }
        lines = [];
    };

    var sortLayers = function(){
        var sortedZ = [];
        var tmpModel = [];

        for(var layer in z_heights){
            sortedZ[z_heights[layer]] = layer;
        }

        sortedZ.sort(function(a,b){
            return a-b;
        });

        for(var i=0;i<sortedZ.length;i++){
            if(typeof(z_heights[sortedZ[i]]) === 'undefined')continue;
            tmpModel[i] = model[z_heights[sortedZ[i]]];
        }
        model = tmpModel;
        delete tmpModel;
    };

    var prepareLinesIndex = function(){
        percentageTree = undefined;

        for (var l in model) {
            for (var i=0; i< model[l].length; i++) {
                var percentage = model[l][i].percentage;
                var value = {layer: l, cmd: i};
                if (!percentageTree) {
                    percentageTree = new AVLTree({key: percentage, value: value}, "key");
                } else {
                    percentageTree.add({key: percentage, value: value});
                }
            }
        }
    };

    var searchInPercentageTree = function(key) {
        if (percentageTree === undefined) {
            return undefined;
        }

        var elements = percentageTree.findBest(key);
        if (elements.length == 0) {
            return undefined;
        }

        return elements[0];
    };

    var purgeLayers = function(){
        var purge=true;
        if(!model){
            console.log("Something terribly wring just happened.");
            return;
        }
        for(var i=0;i<model.length;i++){
            purge=true;
            if(typeof(model[i])==='undefined')purge=true;
            else {
                for(var j=0;j<model[i].length;j++){
                    if(model[i][j].extrude)purge=false;
                }
            }
            if(purge){
                model.splice(i,1);
                i--;
            }
        }
    };



// ***** PUBLIC *******
    return {

        loadFile: function(reader){
            model = [];
            z_heights = [];

            var totalSize = reader.target.result.length;
            lines = reader.target.result.split(/\n/);
            reader.target.result = null;
            prepareGCode(totalSize);

            worker.postMessage({
                    "cmd":"parseGCode",
                    "msg":{
                        gcode: gcode,
                        options: {
                            firstReport: 5
                        }
                    }
                }
            );
            delete lines;
            delete gcode;
        },
        setOption: function(options){
            for(var opt in options){
                gCodeOptions[opt] = options[opt];
            }
        },
        passDataToRenderer: function(){
            if(gCodeOptions["sortLayers"])sortLayers();
            if(gCodeOptions["purgeEmptyLayers"])purgeLayers();
            prepareLinesIndex();
            GCODE.renderer.doRender(model, 0);

        },
        processLayerFromWorker: function(msg){
            model[msg.layerNum] = msg.cmds;
            z_heights[msg.zHeightObject.zValue] = msg.zHeightObject.layer;
        },
        processMultiLayerFromWorker: function(msg){
            for(var i=0;i<msg.layerNum.length;i++){
                model[msg.layerNum[i]] = msg.model[msg.layerNum[i]];
                z_heights[msg.zHeightObject.zValue[i]] = msg.layerNum[i];
            }
        },
        processAnalyzeModelDone: function(msg){
            min = msg.min;
            max = msg.max;
            modelSize = msg.modelSize;
            totalFilament = msg.totalFilament;
            filamentByLayer = msg.filamentByLayer;
            speeds = msg.speeds;
            speedsByLayer = msg.speedsByLayer;
            printTime = msg.printTime;
            printTimeByLayer = msg.printTimeByLayer;
        },
        getLayerFilament: function(z){
            return filamentByLayer[z];
        },
        getLayerSpeeds: function(z){
          return speedsByLayer[z]?speedsByLayer[z]:{};
        },
        getModelInfo: function(){
            return {
                min: min,
                max: max,
                modelSize: modelSize,
                totalFilament: totalFilament,
                speeds: speeds,
                speedsByLayer: speedsByLayer,
                printTime: printTime,
                printTimeByLayer: printTimeByLayer
            };
        },
        getGCodeLines: function(layer, fromSegments, toSegments){
            var i=0;
            var result = {first: model[layer][fromSegments].gcodeLine, last: model[layer][toSegments].gcodeLine};
            return result;
        },
        getCmdIndexForPercentage: function(percentage) {
            var command = searchInPercentageTree(percentage);
            if (command === undefined) {
                return undefined
            } else {
                return command.value;
            }
        }
    }
}());
