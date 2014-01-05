/**
 * User: hudbrog (hudbrog@gmail.com)
 * Date: 10/20/12
 * Time: 1:36 PM
 * To change this template use File | Settings | File Templates.
 */


GCODE.renderer = (function(){
// ***** PRIVATE ******
    var canvas;
    var ctx;
    var zoomFactor= 2.8, zoomFactorDelta = 0.4;
    var scaleF = 0;
    var gridStep=10;
    var ctxHeight, ctxWidth;
    var prevX=0, prevY=0;

    var layerNumStore, progressStore={from: 0, to: -1};
    var lastX, lastY;
    var dragStart,dragged;
    var scaleFactor = 1.1;
    var model;
    var initialized=false;
    var renderOptions = {
        colorGrid: "#bbbbbb",
        bgColorGrid: "#ffffff",
        bgColorOffGrid: "#eeeeee",
        colorLine: ["#000000", "#3333cc", "#cc3333", "#33cc33", "#cc33cc"],
        colorMove: "#00ff00",
        colorRetract: "#ff0000",
        colorRestart: "#0000ff",

        showMoves: true,
        showRetracts: true,
        extrusionWidth: 1,
        // #000000", "#45c7ba",  "#a9533a", "#ff44cc", "#dd1177", "#eeee22", "#ffbb55", "#ff5511", "#777788"
        sizeRetractSpot: 2,
        modelCenter: {x: 0, y: 0},
        differentiateColors: true,
        showNextLayer: false,
        showPreviousLayer: false,

        moveModel: true,
        zoomInOnModel: false,
        zoomInOnBed: false,
        centerViewport: false,

        bed: {x: 200, y: 200},
        container: undefined
    };

    var offsetModelX = 0, offsetModelY = 0;
    var offsetBedX = 0, offsetBedY = 0;
    var speeds = [];
    var speedsByLayer = {};


    var reRender = function(){
        var p1 = ctx.transformedPoint(0,0);
        var p2 = ctx.transformedPoint(canvas.width,canvas.height);
        ctx.clearRect(p1.x,p1.y,p2.x-p1.x,p2.y-p1.y);
        drawGrid();
        if(renderOptions['showNextLayer'] && layerNumStore < model.length - 1) {
            drawLayer(layerNumStore + 1, 0, GCODE.renderer.getLayerNumSegments(layerNumStore + 1), true);
        }
        if (renderOptions['showPreviousLayer'] && layerNumStore > 0) {
            drawLayer(layerNumStore - 1, 0, GCODE.renderer.getLayerNumSegments(layerNumStore - 1), true);
        }
        drawLayer(layerNumStore, progressStore.from, progressStore.to);
    };

    function trackTransforms(ctx){
        var svg = document.createElementNS("http://www.w3.org/2000/svg",'svg');
        var xform = svg.createSVGMatrix();
        ctx.getTransform = function(){ return xform; };

        var savedTransforms = [];
        var save = ctx.save;
        ctx.save = function(){
            savedTransforms.push(xform.translate(0,0));
            return save.call(ctx);
        };
        var restore = ctx.restore;
        ctx.restore = function(){
            xform = savedTransforms.pop();
            return restore.call(ctx);
        };

        var scale = ctx.scale;
        ctx.scale = function(sx,sy){
            xform = xform.scaleNonUniform(sx,sy);
            return scale.call(ctx,sx,sy);
        };
        var rotate = ctx.rotate;
        ctx.rotate = function(radians){
            xform = xform.rotate(radians*180/Math.PI);
            return rotate.call(ctx,radians);
        };
        var translate = ctx.translate;
        ctx.translate = function(dx,dy){
            xform = xform.translate(dx,dy);
            return translate.call(ctx,dx,dy);
        };
        var transform = ctx.transform;
        ctx.transform = function(a,b,c,d,e,f){
            var m2 = svg.createSVGMatrix();
            m2.a=a; m2.b=b; m2.c=c; m2.d=d; m2.e=e; m2.f=f;
            xform = xform.multiply(m2);
            return transform.call(ctx,a,b,c,d,e,f);
        };
        var setTransform = ctx.setTransform;
        ctx.setTransform = function(a,b,c,d,e,f){
            xform.a = a;
            xform.b = b;
            xform.c = c;
            xform.d = d;
            xform.e = e;
            xform.f = f;
            return setTransform.call(ctx,a,b,c,d,e,f);
        };
        var pt  = svg.createSVGPoint();
        ctx.transformedPoint = function(x,y){
            pt.x=x; pt.y=y;
            return pt.matrixTransform(xform.inverse());
        }
    }


    var  startCanvas = function() {
        var jqueryCanvas = $(renderOptions["container"]);
        //jqueryCanvas.css("background-color", renderOptions["bgColorOffGrid"]);
        canvas = jqueryCanvas[0];

        ctx = canvas.getContext('2d');
        ctxHeight = canvas.height;
        ctxWidth = canvas.width;
        lastX = ctxWidth/2;
        lastY = ctxHeight/2;
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        trackTransforms(ctx);

        canvas.addEventListener('mousedown',function(evt){
            document.body.style.mozUserSelect = document.body.style.webkitUserSelect = document.body.style.userSelect = 'none';
            lastX = evt.offsetX || (evt.pageX - canvas.offsetLeft);
            lastY = evt.offsetY || (evt.pageY - canvas.offsetTop);
            dragStart = ctx.transformedPoint(lastX,lastY);
            dragged = false;
        },false);
        canvas.addEventListener('mousemove',function(evt){
            lastX = evt.offsetX || (evt.pageX - canvas.offsetLeft);
            lastY = evt.offsetY || (evt.pageY - canvas.offsetTop);
            dragged = true;
            if (dragStart){
                var pt = ctx.transformedPoint(lastX,lastY);
                ctx.translate(pt.x-dragStart.x,pt.y-dragStart.y);
                reRender();
            }
        },false);
        canvas.addEventListener('mouseup',function(evt){
            dragStart = null;
            if (!dragged) zoom(evt.shiftKey ? -1 : 1 );
        },false);
        var zoom = function(clicks){
            var pt = ctx.transformedPoint(lastX,lastY);
            ctx.translate(pt.x,pt.y);
            var factor = Math.pow(scaleFactor,clicks);
            ctx.scale(factor,factor);
            ctx.translate(-pt.x,-pt.y);
            reRender();
        };
        var handleScroll = function(evt){
            var delta;
            if(evt.detail<0 || evt.wheelDelta>0)delta=zoomFactorDelta;
            else delta=-1*zoomFactorDelta;
            if (delta) zoom(delta);
            return evt.preventDefault() && false;
        };
        canvas.addEventListener('DOMMouseScroll',handleScroll,false);
        canvas.addEventListener('mousewheel',handleScroll,false);

    };

    var drawGrid = function() {
        ctx.translate(offsetBedX, offsetBedY);

        var width = renderOptions["bed"]["x"] * zoomFactor;
        var height = renderOptions["bed"]["y"] * zoomFactor;
        var origin = {
            x: 0,
            y: -1 * renderOptions["bed"]["y"] * zoomFactor
        };
        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2;
        ctx.rect(origin.x, origin.y, width, height);
        ctx.fill();
        ctx.stroke();

        var i;
        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.lineWidth = 1;

        ctx.beginPath();
        for (i = 0; i <= renderOptions["bed"]["x"]; i += gridStep) {
            ctx.moveTo(i * zoomFactor, 0);
            ctx.lineTo(i * zoomFactor, -1 * renderOptions["bed"]["y"] * zoomFactor);
        }
        ctx.stroke();

        ctx.beginPath();
        for (i = 0; i <= renderOptions["bed"]["y"]; i += gridStep) {
            ctx.moveTo(0, -1 * i * zoomFactor);
            ctx.lineTo(renderOptions["bed"]["x"] * zoomFactor, -1 * i * zoomFactor);
        }
        ctx.stroke();

        ctx.translate(-offsetBedX, -offsetBedY);
    };

    var drawLayer = function(layerNum, fromProgress, toProgress, isNotCurrentLayer){
        var i;

        isNotCurrentLayer = typeof isNotCurrentLayer !== 'undefined' ? isNotCurrentLayer : false;
        if (!isNotCurrentLayer) {
            layerNumStore = layerNum;
            progressStore = {from: fromProgress, to: toProgress};
        }

        if (!model || !model[layerNum]) return;

        var cmds = model[layerNum];
        var x, y;

        if (fromProgress > 0) {
            prevX = cmds[fromProgress-1].x * zoomFactor;
            prevY = -cmds[fromProgress-1].y * zoomFactor;
        } else if (fromProgress === 0 && layerNum == 0) {
            if (model[0] && model[0].x !== undefined && model[0].y !== undefined) {
                prevX = model[0].x * zoomFactor;
                prevY = -model[0].y * zoomFactor;
            } else {
                prevX = 0;
                prevY = 0;
            }
        } else if(typeof(cmds[0].prevX) !== 'undefined' && typeof(cmds[0].prevY) !== 'undefined') {
            prevX = cmds[0].prevX * zoomFactor;
            prevY = -cmds[0].prevY * zoomFactor;
        } else {
            if (model[layerNum-1]) {
                prevX = undefined;
                prevY = undefined;
                for (i = model[layerNum-1].length-1; i >= 0; i--) {
                    if (prevX === undefined && model[layerNum-1][i].x !== undefined) prevX = model[layerNum-1][i].x * zoomFactor;
                    if (prevY === undefined && model[layerNum-1][i].y !== undefined) prevY =- model[layerNum-1][i].y * zoomFactor;
                }
                if (prevX === undefined) prevX=0;
                if (prevY === undefined) prevY=0;
            } else {
                prevX = 0;
                prevY = 0;
            }
        }

        for (i = fromProgress; i <= toProgress; i++) {
            ctx.lineWidth = 1;

            if (typeof(cmds[i]) === 'undefined') continue;

            if (typeof(cmds[i].prevX) !== 'undefined' && typeof(cmds[i].prevY) !== 'undefined') {
                prevX = cmds[i].prevX * zoomFactor;
                prevY = -cmds[i].prevY * zoomFactor;
            }

            if (typeof(cmds[i].x) === 'undefined' || isNaN(cmds[i].x)) {
                x = prevX / zoomFactor;
            } else {
                x = cmds[i].x;
            }
            if (typeof(cmds[i].y) === 'undefined' || isNaN(cmds[i].y)) {
                y=prevY/zoomFactor;
            } else {
                y = -cmds[i].y;
            }

            var alpha = (renderOptions['showNextLayer'] || renderOptions['showPreviousLayer']) && isNotCurrentLayer ? 0.3 : 1.0;
            var shade = cmds[i].tool * 0.15;
            if (!cmds[i].extrude && !cmds[i].noMove) {
                if (cmds[i].retract == -1) {
                    if (renderOptions["showRetracts"]) {
                        ctx.strokeStyle = pusher.color(renderOptions["colorRetract"]).shade(shade).alpha(alpha).html();
                        ctx.fillStyle = pusher.color(renderOptions["colorRetract"]).shade(shade).alpha(alpha).html();
                        ctx.beginPath();
                        ctx.arc(prevX, prevY, renderOptions["sizeRetractSpot"], 0, Math.PI*2, true);
                        ctx.stroke();
                        ctx.fill();
                    }
                }
                if(renderOptions["showMoves"]){
                    ctx.strokeStyle = pusher.color(renderOptions["colorMove"]).shade(shade).alpha(alpha).html();
                    ctx.beginPath();
                    ctx.moveTo(prevX, prevY);
                    ctx.lineTo(x*zoomFactor,y*zoomFactor);
                    ctx.stroke();
                }
            } else if(cmds[i].extrude) {
                if (cmds[i].retract == 0) {
                    ctx.strokeStyle = pusher.color(renderOptions["colorLine"][cmds[i].tool]).shade(shade).alpha(alpha).html();
                    ctx.lineWidth = renderOptions['extrusionWidth'];
                    ctx.beginPath();
                    ctx.moveTo(prevX, prevY);
                    ctx.lineTo(x*zoomFactor,y*zoomFactor);
                    ctx.stroke();
                } else {
                    if (renderOptions["showRetracts"]) {
                        ctx.strokeStyle = pusher.color(renderOptions["colorRestart"]).shade(shade).alpha(alpha).html();
                        ctx.fillStyle = pusher.color(renderOptions["colorRestart"]).shade(shade).alpha(alpha).html();
                        ctx.beginPath();
                        ctx.arc(prevX, prevY, renderOptions["sizeRetractSpot"], 0, Math.PI*2, true);
                        ctx.stroke();
                        ctx.fill();
                    }
                }
            }
            prevX = x * zoomFactor;
            prevY = y * zoomFactor;
        }
        ctx.stroke();
    };

    /*
    var calculateBedOffset = function(bedDimensions) {
        if (!bedDimensions) bedDimensions = renderOptions["bed"];

        var max = Math.max(bedDimensions.x, bedDimensions.y);
        return {
            x: (max - bedDimensions.x) / 2 * zoomFactor,
            y: (max - bedDimensions.y) / 2 * zoomFactor
        };
    };

    var applyBedOffset = function(bedDimensions, onlyNew) {
        if (true) return;
        var bedOffset = calculateBedOffset(bedDimensions);

        if (offsetBedX == bedOffset.x && offsetBedY == bedOffset.y) return;

        ctx.translate(-offsetBedX, offsetBedY);
        offsetBedX = bedOffset.x;
        offsetBedY = bedOffset.y;
        ctx.translate(bedOffset.x, -bedOffset.y);
    }
    */


// ***** PUBLIC *******
    return {
        init: function(){
            startCanvas();
            initialized = true;
            zoomFactor = Math.min((canvas.width - 10) / renderOptions["bed"]["x"], (canvas.height - 10) / renderOptions["bed"]["y"]);
            ctx.translate((canvas.width - renderOptions["bed"]["x"] * zoomFactor) / 2, renderOptions["bed"]["y"] * zoomFactor + (canvas.height - renderOptions["bed"]["y"] * zoomFactor) / 2);

            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;

            //applyBedOffset();
        },
        setOption: function(options){
            var mustRefresh = false;
            for (var opt in options) {
                if (options[opt] === undefined) continue;
                if (options.hasOwnProperty(opt)) renderOptions[opt] = options[opt];
                if ($.inArray(opt, ["moveModel", "centerViewport", "zoomInOnModel", "bed"])) {
                    mustRefresh = true;
                }
            }

            if(initialized) {
                if (mustRefresh) {
                    //applyBedOffset();
                    this.refresh();
                } else {
                    reRender();
                }
            }
        },
        getOptions: function(){
            return renderOptions;
        },
        debugGetModel: function(){
            return model;
        },
        render: function(layerNum, fromProgress, toProgress){
            if (!initialized) this.init();

            var p1 = ctx.transformedPoint(0, 0);
            var p2 = ctx.transformedPoint(canvas.width, canvas.height);
            ctx.clearRect(p1.x, p1.y, p2.x - p1.x, p2.y - p1.y);
            drawGrid();
            if (model) {
                if (layerNum < model.length) {
                    if (renderOptions['showNextLayer'] && layerNum < model.length - 1) {
                        drawLayer(layerNum + 1, 0, this.getLayerNumSegments(layerNum + 1), true);
                    }
                    if (renderOptions['showPreviousLayer'] && layerNum > 0) {
                        drawLayer(layerNum - 1, 0, this.getLayerNumSegments(layerNum - 1), true);
                    }
                    drawLayer(layerNum, fromProgress, toProgress);
                } else {
                    console.log("Got request to render non-existent layer");
                }
            }
        },
        getModelNumLayers: function(){
            return model ? model.length : 1;
        },
        getLayerNumSegments: function(layer){
            if(model){
                return model[layer]?model[layer].length:1;
            }else{
                return 1;
            }
        },
        clear: function() {
            model = undefined;
            initialized = false;
            this.render();
        },
        doRender: function(mdl, layerNum){
            model = mdl;
            if (!model || !model[layerNum]) return;

            var mdlInfo;
            prevX = 0;
            prevY = 0;
            if (!initialized) this.init();

            mdlInfo = GCODE.gCodeReader.getModelInfo();
            speeds = mdlInfo.speeds;
            speedsByLayer = mdlInfo.speedsByLayer;

            if (ctx) ctx.translate(-offsetModelX, -offsetModelY);
            if (renderOptions["centerViewport"] || renderOptions["zoomInOnModel"]) {
                offsetModelX = (renderOptions["bed"]["x"] / 2 - (mdlInfo.min.x + mdlInfo.modelSize.x / 2)) * zoomFactor;
                offsetModelY = -1 * (renderOptions["bed"]["y"] / 2 - (mdlInfo.min.y + mdlInfo.modelSize.y / 2)) * zoomFactor;
                offsetBedX = 0;
                offsetBedY = 0;
            } else if (renderOptions["moveModel"]) {
                offsetModelX = (renderOptions["bed"]["x"] / 2 - (mdlInfo.min.x + mdlInfo.modelSize.x / 2)) * zoomFactor;
                offsetModelY = -1 * (renderOptions["bed"]["y"] / 2 - (mdlInfo.min.y + mdlInfo.modelSize.y / 2)) * zoomFactor;
                offsetBedX = -1 * (renderOptions["bed"]["x"] / 2 - (mdlInfo.min.x + mdlInfo.modelSize.x / 2)) * zoomFactor;
                offsetBedY = (renderOptions["bed"]["y"] / 2 - (mdlInfo.min.y + mdlInfo.modelSize.y / 2)) * zoomFactor;
            } else {
                offsetModelX = 0;
                offsetModelY = 0;
                offsetBedX = 0;
                offsetBedY = 0;
            }
            if (ctx) ctx.translate(offsetModelX, offsetModelY);

            var pt = ctx.transformedPoint(canvas.width/2,canvas.height/2);
            var transform = ctx.getTransform();
            var scaleX, scaleY;
            if (scaleF && transform.a && transform.d) {
                scaleX = scaleF / transform.a;
                scaleY = scaleF / transform.d;
                ctx.translate(pt.x, pt.y);
                ctx.scale(1 / (0.98 * scaleX), 1 / (0.98 * scaleY));
                ctx.translate(-pt.x, -pt.y);
                pt = ctx.transformedPoint(canvas.width/2,canvas.height/2);
            }
            if (renderOptions["zoomInOnModel"]) {
                scaleF = mdlInfo.modelSize.x > mdlInfo.modelSize.y ? (canvas.width) / mdlInfo.modelSize.x / zoomFactor : (canvas.height) / mdlInfo.modelSize.y / zoomFactor;
                if (transform.a && transform.d) {
                    scaleX = scaleF / transform.a;
                    scaleY = scaleF / transform.d;
                    ctx.translate(pt.x,pt.y);
                    ctx.scale(0.98 * scaleX, 0.98 * scaleY);
                    ctx.translate(-pt.x, -pt.y);
                }
            } else {
                scaleF = 0;
            }

            this.render(layerNum, 0, model[layerNum].length);
        },
        refresh: function(layerNum) {
            if (!layerNum) layerNum = layerNumStore;
            this.doRender(model, layerNum);
        },
        getZ: function(layerNum){
            if(!model || !model[layerNum]){
                return '-1';
            }
            var cmds = model[layerNum];
            for(var i = 0; i < cmds.length; i++){
                if(cmds[i].prevZ !== undefined) return cmds[i].prevZ;
            }
            return '-1';
        }

}
}());
