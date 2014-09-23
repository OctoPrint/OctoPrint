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
    var gridStep=10;
    var ctxHeight, ctxWidth;
    var prevX=0, prevY=0;

    var layerNumStore, progressStore={from: 0, to: -1};
    var lastX, lastY;
    var dragStart, dragged;
    var scaleFactor = 1.1;
    var model;
    var initialized = false;
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
        invertAxes: {x: false, y: false},

        bed: {x: 200, y: 200},
        container: undefined,

        onInternalOptionChange: undefined
    };

    var offsetModelX = 0, offsetModelY = 0;
    var offsetBedX = 0, offsetBedY = 0;
    var scaleX = 1, scaleY = 1;
    var speeds = [];
    var speedsByLayer = {};
    var currentInvertX = false, currentInvertY = false;

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

        // dragging => translating
        canvas.addEventListener('mousedown', function(event){
            document.body.style.mozUserSelect = document.body.style.webkitUserSelect = document.body.style.userSelect = 'none';

            // remember starting point of dragging gesture
            lastX = event.offsetX || (event.pageX - canvas.offsetLeft);
            lastY = event.offsetY || (event.pageY - canvas.offsetTop);
            dragStart = ctx.transformedPoint(lastX, lastY);

            // not yet dragged anything
            dragged = false;
        }, false);

        canvas.addEventListener('mousemove', function(event){
            // save current mouse coordinates
            lastX = event.offsetX || (event.pageX - canvas.offsetLeft);
            lastY = event.offsetY || (event.pageY - canvas.offsetTop);

            // mouse movement => dragged
            dragged = true;

            if (dragStart !== undefined){
                // translate
                var pt = ctx.transformedPoint(lastX,lastY);
                ctx.translate(pt.x - dragStart.x, pt.y - dragStart.y);
                reRender();

                renderOptions["centerViewport"] = false;
                renderOptions["zoomInOnModel"] = false;
                renderOptions["zoomInOnBed"] = false;
                offsetModelX = 0;
                offsetModelY = 0;
                offsetBedX = 0;
                offsetBedY = 0;
                scaleX = 1;
                scaleY = 1;

                if (renderOptions["onInternalOptionChange"] !== undefined) {
                    renderOptions["onInternalOptionChange"]({
                        centerViewport: false,
                        moveModel: false,
                        zoomInOnModel: false,
                        zoomInOnBed: false
                    });
                }
            }
        }, false);

        canvas.addEventListener('mouseup', function(event){
            // reset dragStart
            dragStart = undefined;
        }, false);

        // mouse wheel => zooming
        var zoom = function(clicks){
            // focus on last mouse position prior to zoom
            var pt = ctx.transformedPoint(lastX, lastY);
            ctx.translate(pt.x,pt.y);

            // determine zooming factor and perform zoom
            var factor = Math.pow(scaleFactor,clicks);
            ctx.scale(factor,factor);

            // return to old position
            ctx.translate(-pt.x,-pt.y);

            // render
            reRender();

            // disable conflicting options
            renderOptions["zoomInOnModel"] = false;
            renderOptions["zoomInOnBed"] = false;
            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;
            scaleX = 1;
            scaleY = 1;

            if (renderOptions["onInternalOptionChange"] !== undefined) {
                renderOptions["onInternalOptionChange"]({
                    zoomInOnModel: false,
                    zoomInOnBed: false
                });
            }
        };
        var handleScroll = function(event){
            var delta;

            // determine zoom direction & delta
            if (event.detail < 0 || event.wheelDelta > 0) {
                delta = zoomFactorDelta;
            } else {
                delta = -1 * zoomFactorDelta;
            }
            if (delta) zoom(delta);

            return event.preventDefault() && false;
        };
        canvas.addEventListener('DOMMouseScroll',handleScroll,false);
        canvas.addEventListener('mousewheel',handleScroll,false);
    };

    var drawGrid = function() {
        ctx.translate(offsetBedX, offsetBedY);
        if(renderOptions["bed"]["circular"]) {
            drawCircularGrid();
        } else {
            drawRectangularGrid();
        }
        ctx.translate(-offsetBedX, -offsetBedY);
    };

    var drawRectangularGrid = function() {
        var i;
        var width = renderOptions["bed"]["x"] * zoomFactor;
        var height = renderOptions["bed"]["y"] * zoomFactor;
        var origin = {
            x: 0,
            y: -1 * renderOptions["bed"]["y"] * zoomFactor
        };

        ctx.beginPath();
        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2;

        ctx.rect(origin.x, origin.y, width, height);

        ctx.fill();
        ctx.stroke();

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
    };

    var drawCircularGrid = function() {
        var i;

        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2;

        //~~ bed outline & origin
        ctx.beginPath();

        // outline
        ctx.arc(0, 0, renderOptions["bed"]["r"] * zoomFactor, 0, Math.PI * 2, true);

        // origin
        ctx.moveTo(-1 * renderOptions["bed"]["r"] * zoomFactor, 0);
        ctx.lineTo(renderOptions["bed"]["r"] * zoomFactor, 0);
        ctx.moveTo(0, -1 * renderOptions["bed"]["r"] * zoomFactor);
        ctx.lineTo(0, renderOptions["bed"]["r"] * zoomFactor);

        // draw
        ctx.fill();
        ctx.stroke();

        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.lineWidth = 1;

        //~~ grid starting from origin
        ctx.beginPath();
        for (i = 0; i <= renderOptions["bed"]["r"]; i += gridStep) {
            var x = i;
            var y = Math.sqrt(Math.pow(renderOptions["bed"]["r"], 2) - Math.pow(x, 2));

            ctx.moveTo(x * zoomFactor, y * zoomFactor);
            ctx.lineTo(x * zoomFactor, -1 * y * zoomFactor);

            ctx.moveTo(y * zoomFactor, x * zoomFactor);
            ctx.lineTo(-1 * y * zoomFactor, x * zoomFactor);

            ctx.moveTo(-1 * x * zoomFactor, y * zoomFactor);
            ctx.lineTo(-1 * x * zoomFactor, -1 * y * zoomFactor);

            ctx.moveTo(y * zoomFactor, -1 * x * zoomFactor);
            ctx.lineTo(-1 * y * zoomFactor, -1 * x * zoomFactor);
        }
        ctx.stroke();
    };

    var drawLayer = function(layerNum, fromProgress, toProgress, isNotCurrentLayer){
        console.log("Drawing layer " + layerNum + " from " + fromProgress + " to " + toProgress + " (current: " + !isNotCurrentLayer + ")");

        var i;

        //~~ store current layer values

        isNotCurrentLayer = isNotCurrentLayer !== undefined ? isNotCurrentLayer : false;
        if (!isNotCurrentLayer) {
            // not not current layer == current layer => store layer number and from/to progress
            layerNumStore = layerNum;
            progressStore = {from: fromProgress, to: toProgress};
        }

        if (!model || !model[layerNum]) return;

        var cmds = model[layerNum];
        var x, y;

        //~~ find our initial prevX/prevY tuple

        if (cmds[0].prevX !== undefined && cmds[0].prevY !== undefined) {
            // command contains prevX/prevY values, use those
            prevX = cmds[0].prevX * zoomFactor;
            prevY = -1 * cmds[0].prevY * zoomFactor;
        } else if (fromProgress > 0) {
            // previous command in same layer exists, use x/y as prevX/prevY
            prevX = cmds[fromProgress - 1].x * zoomFactor;
            prevY = -cmds[fromProgress - 1].y * zoomFactor;
        } else if (model[layerNum - 1]) {
            // previous layer exists, use last x/y as prevX/prevY
            prevX = undefined;
            prevY = undefined;
            for (i = model[layerNum-1].length-1; i >= 0; i--) {
                if (prevX === undefined && model[layerNum - 1][i].x !== undefined) prevX = model[layerNum - 1][i].x * zoomFactor;
                if (prevY === undefined && model[layerNum - 1][i].y !== undefined) prevY =- model[layerNum - 1][i].y * zoomFactor;
            }
        }

        // if we did not find prevX or prevY, set it to 0 (might be that we are on the first command of the first layer,
        // or it's just a very weird model...)
        if (prevX === undefined) prevX = 0;
        if (prevY === undefined) prevY = 0;

        //~~ render this layer's commands

        for (i = fromProgress; i <= toProgress; i++) {
            ctx.lineWidth = 1;

            if (typeof(cmds[i]) === 'undefined') continue;

            if (typeof(cmds[i].prevX) !== 'undefined' && typeof(cmds[i].prevY) !== 'undefined') {
                // override new (prevX, prevY)
                prevX = cmds[i].prevX * zoomFactor;
                prevY = -1 * cmds[i].prevY * zoomFactor;
            }

            // new x
            if (typeof(cmds[i].x) === 'undefined' || isNaN(cmds[i].x)) {
                x = prevX / zoomFactor;
            } else {
                x = cmds[i].x;
            }

            // new y
            if (typeof(cmds[i].y) === 'undefined' || isNaN(cmds[i].y)) {
                y = prevY / zoomFactor;
            } else {
                y = -cmds[i].y;
            }

            // current tool
            var tool = cmds[i].tool;
            if (tool === undefined) tool = 0;

            // line color based on tool
            var lineColor = renderOptions["colorLine"][tool];
            if (lineColor === undefined) lineColor = renderOptions["colorLine"][0];

            // alpha value (100% if current layer is being rendered, 30% otherwise)
            var alpha = (renderOptions['showNextLayer'] || renderOptions['showPreviousLayer']) && isNotCurrentLayer ? 0.3 : 1.0;
            var shade = tool * 0.15;

            if (!cmds[i].extrude && !cmds[i].noMove) {
                // neither extrusion nor move
                if (cmds[i].retract == -1) {
                    // retract => draw dot if configured to do so
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
                    // move => draw line from (prevX, prevY) to (x, y) in move color
                    ctx.strokeStyle = pusher.color(renderOptions["colorMove"]).shade(shade).alpha(alpha).html();
                    ctx.beginPath();
                    ctx.moveTo(prevX, prevY);
                    ctx.lineTo(x*zoomFactor,y*zoomFactor);
                    ctx.stroke();
                }
            } else if(cmds[i].extrude) {
                if (cmds[i].retract == 0) {
                    // no retraction => real extrusion move, use tool color to draw line
                    ctx.strokeStyle = pusher.color(renderOptions["colorLine"][tool]).shade(shade).alpha(alpha).html();
                    ctx.lineWidth = renderOptions['extrusionWidth'];
                    ctx.beginPath();
                    ctx.moveTo(prevX, prevY);
                    ctx.lineTo(x*zoomFactor,y*zoomFactor);
                    ctx.stroke();
                } else {
                    // we were previously retracting, now we are restarting => draw dot if configured to do so
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

            // set new (prevX, prevY)
            prevX = x * zoomFactor;
            prevY = y * zoomFactor;
        }
        ctx.stroke();
    };

    var applyOffsets = function(mdlInfo) {
        var canvasCenter;

        // determine bed and model offsets
        if (ctx) ctx.translate(-offsetModelX, -offsetModelY);
        if (renderOptions["centerViewport"] || renderOptions["zoomInOnModel"]) {
            canvasCenter = ctx.transformedPoint(canvas.width / 2, canvas.height / 2);
            if (mdlInfo) {
                offsetModelX = canvasCenter.x - (mdlInfo.min.x + mdlInfo.modelSize.x / 2) * zoomFactor;
                offsetModelY = canvasCenter.y + (mdlInfo.min.y + mdlInfo.modelSize.y / 2) * zoomFactor;
            } else {
                offsetModelX = 0;
                offsetModelY = 0;
            }
            offsetBedX = 0;
            offsetBedY = 0;
        } else if (mdlInfo && renderOptions["moveModel"]) {
            offsetModelX = (renderOptions["bed"]["x"] / 2 - (mdlInfo.min.x + mdlInfo.modelSize.x / 2)) * zoomFactor;
            offsetModelY = -1 * (renderOptions["bed"]["y"] / 2 - (mdlInfo.min.y + mdlInfo.modelSize.y / 2)) * zoomFactor;
            offsetBedX = -1 * (renderOptions["bed"]["x"] / 2 - (mdlInfo.min.x + mdlInfo.modelSize.x / 2)) * zoomFactor;
            offsetBedY = (renderOptions["bed"]["y"] / 2 - (mdlInfo.min.y + mdlInfo.modelSize.y / 2)) * zoomFactor;
        } else if (renderOptions["bed"]["circular"]) {
            canvasCenter = ctx.transformedPoint(canvas.width / 2, canvas.height / 2);
            offsetModelX = canvasCenter.x;
            offsetModelY = canvasCenter.y;
            offsetBedX = 0;
            offsetBedY = 0;
        } else {
            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;
        }
        if (ctx) ctx.translate(offsetModelX, offsetModelY);
    };

    var applyZoom = function(mdlInfo) {
        // get middle of canvas
        var pt = ctx.transformedPoint(canvas.width/2,canvas.height/2);

        // get current transform
        var transform = ctx.getTransform();

        // move to middle of canvas, reset scale, move back
        if (scaleX && scaleY && transform.a && transform.d) {
            ctx.translate(pt.x, pt.y);
            ctx.scale(1 / scaleX, 1 / scaleY);
            ctx.translate(-pt.x, -pt.y);
            transform = ctx.getTransform();
        }

        if (mdlInfo && renderOptions["zoomInOnModel"]) {
            // if we need to zoom in on model, scale factor is calculated by longer side of object in relation to that axis of canvas
            var scaleF = mdlInfo.modelSize.x > mdlInfo.modelSize.y ? (canvas.width - 10) / mdlInfo.modelSize.x : (canvas.height - 10) / mdlInfo.modelSize.y;
            scaleF /= zoomFactor;
            if (transform.a && transform.d) {
                scaleX = scaleF / transform.a * (renderOptions["invertAxes"]["x"] ? -1 : 1);
                scaleY = scaleF / transform.d * (renderOptions["invertAxes"]["y"] ? -1 : 1);
                ctx.translate(pt.x,pt.y);
                ctx.scale(scaleX, scaleY);
                ctx.translate(-pt.x, -pt.y);
            }
        } else {
            // reset scale to 1
            scaleX = 1;
            scaleY = 1;
        }
    };

    var applyInversion = function() {
        var width = canvas.width - 10;
        var height = canvas.height - 10;

        // de-invert
        if (currentInvertX || currentInvertY) {
            ctx.scale(currentInvertX ? -1 : 1, currentInvertY ? -1 : 1);
            ctx.translate(currentInvertX ? -width : 0, currentInvertY ? height : 0);
        }

        // get settings
        var invertX = renderOptions["invertAxes"]["x"];
        var invertY = renderOptions["invertAxes"]["y"];

        // invert
        if (invertX || invertY) {
            ctx.translate(invertX ? width : 0, invertY ? -height : 0);
            ctx.scale(invertX ? -1 : 1, invertY ? -1 : 1);
        }

        // save for later
        currentInvertX = invertX;
        currentInvertY = invertY;
    };

// ***** PUBLIC *******
    return {
        init: function(){
            startCanvas();
            initialized = true;
            var bedWidth = renderOptions["bed"]["x"];
            var bedHeight = renderOptions["bed"]["y"];
            if(renderOptions["bed"]["circular"]) {
                bedWidth = bedHeight = renderOptions["bed"]["r"] * 2;
            }
            zoomFactor = Math.min((canvas.width - 10) / bedWidth, (canvas.height - 10) / bedHeight);

            var translationX, translationY;
            if (renderOptions["bed"]["circular"]) {
                translationX = canvas.width / 2;
                translationY = canvas.height / 2;
            } else {
                translationX = (canvas.width - bedWidth * zoomFactor) / 2;
                translationY = bedHeight * zoomFactor + (canvas.height - bedHeight * zoomFactor) / 2;
            }
            ctx.translate(translationX, translationY);

            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;
        },
        setOption: function(options){
            var mustRefresh = false;
            var dirty = false;
            for (var opt in options) {
                if (!renderOptions.hasOwnProperty(opt) || !options.hasOwnProperty(opt)) continue;
                if (options[opt] === undefined) continue;
                if (renderOptions[opt] == options[opt]) continue;

                dirty = true;
                renderOptions[opt] = options[opt];
                if ($.inArray(opt, ["moveModel", "centerViewport", "zoomInOnModel", "bed", "invertAxes"]) > -1) {
                    mustRefresh = true;
                }
            }

            if (!dirty) return;
            if(initialized) {
                if (mustRefresh) {
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
            if (model && model.length) {
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
            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;
            scaleX = 1;
            scaleY = 1;
            speeds = [];
            speedsByLayer = {};

            this.doRender([], 0);
        },
        doRender: function(mdl, layerNum){
            model = mdl;

            var mdlInfo = undefined;
            prevX = 0;
            prevY = 0;
            if (!initialized) this.init();

            var toProgress = 1;
            if (model) {
                mdlInfo = GCODE.gCodeReader.getModelInfo();
                speeds = mdlInfo.speeds;
                speedsByLayer = mdlInfo.speedsByLayer;
                if (model[layerNum]) {
                    toProgress = model[layerNum].length;
                }
            }

            applyInversion();
            applyOffsets(mdlInfo);
            applyZoom(mdlInfo);

            this.render(layerNum, 0, toProgress);
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
