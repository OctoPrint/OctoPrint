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

    var viewportChanged = true;
    var lineWidthFactor = 1 / 2.8;

    var zoomFactorDelta = 0.4;
    var gridStep=10;
    var ctxHeight, ctxWidth;
    var prevX=0, prevY=0;
    var pixelRatio = window.devicePixelRatio || 1;

    var layerNumStore, progressStore={from: 0, to: -1};
    var lastX, lastY;
    var dragStart;
    var scaleFactor = 1.1;
    var model = undefined;
    var modelInfo = undefined;
    var initialized = false;
    var renderOptions = {
        colorGrid: "#bbbbbb",
        bgColorGrid: "#ffffff",
        bgColorOffGrid: "#eeeeee",
        colorLine: ["#000000", "#3333cc", "#cc3333", "#33cc33", "#cc33cc"],
        colorMove: "#00ff00",
        colorRetract: "#ff0000",
        colorRestart: "#0000ff",
        colorHead: "#00ff00",

        showMoves: true,
        showRetracts: true,
        extrusionWidth: 1 * pixelRatio,
        // #000000", "#45c7ba",  "#a9533a", "#ff44cc", "#dd1177", "#eeee22", "#ffbb55", "#ff5511", "#777788"
        sizeRetractSpot: 2 * pixelRatio,
        sizeHeadSpot: 2 * pixelRatio,
        modelCenter: {x: 0, y: 0},
        differentiateColors: true,
        showNextLayer: false,
        showCurrentLayer: false,
        showPreviousLayer: false,
        showBoundingBox: false,
        showFullSize: false,
        showHead: false,

        moveModel: true,
        zoomInOnModel: false,
        zoomInOnBed: false,
        centerViewport: false,
        invertAxes: {x: false, y: false},

        bed: {x: 200, y: 200},
        container: undefined,

        onInternalOptionChange: undefined,

        onViewportChange: undefined,
        onDragStart: undefined, // Cancellable (return false)
        onDrag: undefined,      // Cancellable (return false)
        onDragStop: undefined
    };

    var offsetModelX = 0, offsetModelY = 0;
    var offsetBedX = 0, offsetBedY = 0;
    var scaleX = 1, scaleY = 1;
    var speeds = [];
    var speedsByLayer = {};
    var currentInvertX = false, currentInvertY = false;

    function notifyIfViewportChanged() {
        if (viewportChanged) {
            if (renderOptions["onViewportChange"]) {
                renderOptions["onViewportChange"](ctx.getTransform());
            }
            viewportChanged = false;
        }
    }
    
    var reRender = function(){
        if (!model) return;

        log.debug("Rerendering layer " + layerNumStore + " of " + model.length + " with " + GCODE.renderer.getLayerNumSegments(layerNumStore) + " segments");

        notifyIfViewportChanged();

        var p1 = ctx.transformedPoint(0,0);
        var p2 = ctx.transformedPoint(canvas.width,canvas.height);
        ctx.clearRect(p1.x,p1.y,p2.x-p1.x,p2.y-p1.y);

        drawGrid();
        drawBoundingBox();
        if (model && model.length) {
            if (layerNumStore < model.length) {
                if (renderOptions['showNextLayer'] && layerNumStore < model.length - 1) {
                    drawLayer(layerNumStore + 1, 0, GCODE.renderer.getLayerNumSegments(layerNumStore + 1), true);
                }
                if (renderOptions['showCurrentLayer'] && layerNumStore < model.length) {
                    drawLayer(layerNumStore, 0, GCODE.renderer.getLayerNumSegments(layerNumStore), true);
                }
                if (renderOptions['showPreviousLayer'] && layerNumStore > 0) {
                    drawLayer(layerNumStore - 1, 0, GCODE.renderer.getLayerNumSegments(layerNumStore - 1), true);
                }
                drawLayer(layerNumStore, progressStore.from, progressStore.to);
            } else {
                console.log("Got request to render non-existent layer");
            }
        }
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
            viewportChanged = true;
            return restore.call(ctx);
        };

        var scale = ctx.scale;
        ctx.scale = function(sx,sy){
            xform = xform.scaleNonUniform(sx,sy);
            viewportChanged = true;
            return scale.call(ctx,sx,sy);
        };
        var rotate = ctx.rotate;
        ctx.rotate = function(radians){
            xform = xform.rotate(radians*180/Math.PI);
            viewportChanged = true;
            return rotate.call(ctx,radians);
        };
        var translate = ctx.translate;
        ctx.translate = function(dx,dy){
            xform = xform.translate(dx,dy);
            viewportChanged = true;
            return translate.call(ctx,dx,dy);
        };
        var transform = ctx.transform;
        ctx.transform = function(a,b,c,d,e,f){
            var m2 = svg.createSVGMatrix();
            m2.a=a; m2.b=b; m2.c=c; m2.d=d; m2.e=e; m2.f=f;
            xform = xform.multiply(m2);
            viewportChanged = true;
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
            viewportChanged = true;
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
        canvas.style.height = canvas.height + "px";
        canvas.style.width = canvas.width + "px";
        canvas.height = canvas.height * pixelRatio;
        canvas.width = canvas.width * pixelRatio;
        ctxHeight = canvas.height;
        ctxWidth = canvas.width;
        lastX = ctxWidth/2;
        lastY = ctxHeight/2;
        ctx.lineWidth = 2 * lineWidthFactor;
        ctx.lineCap = 'round';
        trackTransforms(ctx);

        ctx.scale(1,-1); // Invert y-axis

        // dragging => translating
        canvas.addEventListener('mousedown', function(event){
            document.body.style.mozUserSelect = document.body.style.webkitUserSelect = document.body.style.userSelect = 'none';

            // remember starting point of dragging gesture
            lastX = (event.offsetX || (event.pageX - canvas.offsetLeft)) * pixelRatio;
            lastY = (event.offsetY || (event.pageY - canvas.offsetTop)) * pixelRatio;

            var pt = ctx.transformedPoint(lastX, lastY);
            if (!renderOptions["onDragStart"] || (renderOptions["onDragStart"](pt) !== false))
              dragStart = pt;
        }, false);

        canvas.addEventListener('mousemove', function(event){
            // save current mouse coordinates
            lastX = (event.offsetX || (event.pageX - canvas.offsetLeft)) * pixelRatio;
            lastY = (event.offsetY || (event.pageY - canvas.offsetTop)) * pixelRatio;

            // mouse movement => dragged
            if (dragStart !== undefined) {
                // translate
                var pt = ctx.transformedPoint(lastX,lastY);

                if (renderOptions["onDrag"] && (renderOptions["onDrag"](pt) === false))
                    return;

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

            if (renderOptions["onDragStop"]) {
                var x = (event.offsetX || (event.pageX - canvas.offsetLeft)) * pixelRatio;
                var y = (event.offsetY || (event.pageY - canvas.offsetTop)) * pixelRatio;
                renderOptions["onDragStop"](ctx.transformedPoint(x,y));
            }
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
        var x, y;
        var width = renderOptions["bed"]["x"];
        var height = renderOptions["bed"]["y"];

        var minX, maxX, minY, maxY;
        if (renderOptions["bed"]["centeredOrigin"]) {
            var halfWidth = width / 2;
            var halfHeight = height / 2;

            minX = -halfWidth;
            maxX = halfWidth;
            minY = -halfHeight;
            maxY = halfHeight;
        } else {
            minX = 0;
            maxX = width;
            minY = 0;
            maxY = height;
        }

        //~ bed outline and origin
        ctx.beginPath();
        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2 * lineWidthFactor;

        // outline
        ctx.rect(minX, minY, width, height);

        // origin
        ctx.moveTo(minX, 0);
        ctx.lineTo(maxX, 0);
        ctx.moveTo(0, minY);
        ctx.lineTo(0, maxY);

        // draw
        ctx.fill();
        ctx.stroke();

        // draw origin
        ctx.beginPath();
        ctx.arc(0, 0, 2, 0, Math.PI * 2, true);
        ctx.stroke();

        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.lineWidth = lineWidthFactor;

        //~~ grid starting from origin
        ctx.beginPath();
        for (x = 0; x <= maxX; x += gridStep) {
            ctx.moveTo(x, minY);
            ctx.lineTo(x, maxY);

            if (renderOptions["bed"]["centeredOrigin"]) {
                ctx.moveTo(-1 * x, minY);
                ctx.lineTo(-1 * x, maxY);
            }
        }
        ctx.stroke();

        ctx.beginPath();
        for (y = 0; y <= maxY; y += gridStep) {
            ctx.moveTo(minX, y);
            ctx.lineTo(maxX, y);

            if (renderOptions["bed"]["centeredOrigin"]) {
                ctx.moveTo(minX, -1 * y);
                ctx.lineTo(maxX, -1 * y);
            }
        }
        ctx.stroke();
    };

    var drawCircularGrid = function() {
        var i;

        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.fillStyle = "#ffffff";
        ctx.lineWidth = 2 * lineWidthFactor;

        //~~ bed outline & origin
        ctx.beginPath();

        // outline
        var r = renderOptions["bed"]["r"];
        ctx.arc(0, 0, r, 0, Math.PI * 2, true);

        // origin
        ctx.moveTo(-1 * r, 0);
        ctx.lineTo(r, 0);
        ctx.moveTo(0, r);
        ctx.lineTo(0, -1 * r);

        // draw
        ctx.fill();
        ctx.stroke();

        // draw origin
        ctx.beginPath();
        ctx.arc(0, 0, 2, 0, Math.PI * 2, true);
        ctx.stroke();

        ctx.strokeStyle = renderOptions["colorGrid"];
        ctx.lineWidth = lineWidthFactor;

        //~~ grid starting from origin
        ctx.beginPath();
        for (i = 0; i <= r; i += gridStep) {
            var x = i;
            var y = Math.sqrt(r*r - x*x);

            ctx.moveTo(x, -1 * y);
            ctx.lineTo(x, y);

            ctx.moveTo(y, -1 * x);
            ctx.lineTo(-1 * y, -1 * x);

            ctx.moveTo(-1 * x, -1 * y);
            ctx.lineTo(-1 * x, y);

            ctx.moveTo(y, x);
            ctx.lineTo(-1 * y, x);
        }
        ctx.stroke();
    };

    var drawBoundingBox = function() {
        if (!modelInfo) return;

        var minX, minY, width, height;

        if (renderOptions["showFullSize"]) {
            minX = modelInfo.min.x;
            minY = modelInfo.min.y;
            width = modelInfo.modelSize.x;
            height = modelInfo.modelSize.y;

            ctx.beginPath();
            ctx.strokeStyle = "#0000ff";
            ctx.setLineDash([2, 5]);

            ctx.rect(minX, minY, width, height);

            ctx.stroke();
        }

        if (renderOptions["showBoundingBox"]) {
            minX = modelInfo.boundingBox.minX;
            minY = modelInfo.boundingBox.minY;
            width = modelInfo.boundingBox.maxX - minX;
            height = modelInfo.boundingBox.maxY - minY;

            ctx.beginPath();
            ctx.strokeStyle = "#ff0000";
            ctx.setLineDash([2, 5]);

            ctx.rect(minX, minY, width, height);

            ctx.stroke();
        }

        ctx.setLineDash([1, 0]);
    };

    var drawTriangle = function(centerX, centerY, length, up) {
        /*
         *             (cx,cy)
         *                *             ^
         *               / \            |
         *              /   \           |
         *             /     \          |
         *            / (x,y) \         | h
         *           /         \        |
         *          /           \       |
         *         /             \      |
         *        *---------------*     v
         *    (ax,ay)           (bx,by)
         */

        var ax, bx, cx, ay, by, cy;
        var h = Math.sqrt(0.75 * length * length) / 2;

        ax = centerX - length / 2;
        bx = ax + length;
        cx = centerX;

        if (up) {
            ay = centerY - h;
            by = centerY - h;
            cy = centerY + h;
        } else {
            ay = centerY + h;
            by = centerY + h;
            cy = centerY - h;
        }

        var origLineJoin = ctx.lineJoin;
        ctx.lineJoin = "miter";

        ctx.beginPath();
        ctx.moveTo(ax, ay);
        ctx.lineTo(bx, by);
        ctx.moveTo(bx, by);
        ctx.lineTo(cx, cy);
        ctx.lineTo(ax, ay);
        ctx.stroke();
        ctx.fill();

        ctx.lineJoin = origLineJoin;
    };

    var drawLayer = function(layerNum, fromProgress, toProgress, isNotCurrentLayer){
        log.trace("Drawing layer " + layerNum + " from " + fromProgress + " to " + toProgress + " (current: " + !isNotCurrentLayer + ")");

        var i;

        //~~ store current layer values

        isNotCurrentLayer = isNotCurrentLayer !== undefined ? isNotCurrentLayer : false;

        if (!model || !model[layerNum]) return;

        var cmds = model[layerNum];
        var x, y;

        //~~ find our initial prevX/prevY tuple

        if (cmds[0].prevX !== undefined && cmds[0].prevY !== undefined) {
            // command contains prevX/prevY values, use those
            prevX = cmds[0].prevX;
            prevY = cmds[0].prevY;
        } else if (fromProgress > 0) {
            // previous command in same layer exists, use x/y as prevX/prevY
            prevX = cmds[fromProgress - 1].x;
            prevY = cmds[fromProgress - 1].y;
        } else if (model[layerNum - 1]) {
            // previous layer exists, use last x/y as prevX/prevY
            prevX = undefined;
            prevY = undefined;
            var prevModelLayer = model[layerNum-1];
            for (i = prevModelLayer.length-1; i >= 0; i--) {
                if (prevX === undefined && prevModelLayer[i].x !== undefined) {
                    prevX = prevModelLayer[i].x;
                    if (prevY !== undefined)
                        break;
                }
                if (prevY === undefined && prevModelLayer[i].y !== undefined) {
                    prevY = prevModelLayer[i].y;
                    if (prevX !== undefined)
                        break;
                }
            }
        }

        // if we did not find prevX or prevY, set it to 0 (might be that we are on the first command of the first layer,
        // or it's just a very weird model...)
        if (prevX === undefined) prevX = 0;
        if (prevY === undefined) prevY = 0;

        //~~ render this layer's commands

        var sizeRetractSpot = renderOptions["sizeRetractSpot"] * lineWidthFactor * 2;

        // alpha value (100% if current layer is being rendered, 30% otherwise)
        // Note - If showing currently layer as preview - also render it at 30% and draw the progress over the top at 100%
        var alpha = (renderOptions['showNextLayer'] || renderOptions['showCurrentLayer'] || renderOptions['showPreviousLayer']) && isNotCurrentLayer ? 0.3 : 1.0;
        
        var colorLine = {};
        var colorMove = {};
        var colorRetract = {};
        var colorRestart = {};

        function getColorLineForTool(tool) {
            var rv = colorLine[tool];
            if (rv === undefined) {
                var lineColor = renderOptions["colorLine"][tool];
                if (lineColor === undefined) lineColor = renderOptions["colorLine"][0];
                var shade = tool * 0.15;
                rv = colorLine[tool] = pusher.color(lineColor).shade(shade).alpha(alpha).html();
            }
            return rv;
        }

        function getColorMoveForTool(tool) {
            var rv = colorMove[tool];
            if (rv === undefined) {
                var shade = tool * 0.15;
                rv = colorMove[tool] = pusher.color(renderOptions["colorMove"]).shade(shade).alpha(alpha).html();
            }
            return rv;
        }

        function getColorRetractForTool(tool) {
            var rv = colorRetract[tool];
            if (rv === undefined) {
                var shade = tool * 0.15;
                rv = colorRetract[tool] = pusher.color(renderOptions["colorRetract"]).shade(shade).alpha(alpha).html();
            }
            return rv;
        }

        function getColorRestartForTool(tool) {
            var rv = colorRestart[tool];
            if (rv === undefined) {
                var shade = tool * 0.15;
                rv = colorRestart[tool] = pusher.color(renderOptions["colorRestart"]).shade(shade).alpha(alpha).html();
            }
            return rv;
        }

        var prevPathType = "fill";
        function strokePathIfNeeded(newPathType, strokeStyle) {
            if ((newPathType != prevPathType) || (newPathType == "fill")) {
                if (prevPathType != "fill") {
                    ctx.stroke();
                }
                prevPathType = newPathType;

                ctx.beginPath();
                if (newPathType != "fill") {
                  ctx.strokeStyle = strokeStyle;
                  ctx.moveTo(prevX, prevY);
                }
            }
        }

        ctx.lineJoin = "round";

        for (i = fromProgress; i <= toProgress; i++) {
            if (typeof(cmds[i]) === 'undefined') continue;
            var cmd = cmds[i];

            if (cmd.prevX !== undefined && cmd.prevY !== undefined) {
                // override new (prevX, prevY)
                prevX = cmd.prevX;
                prevY = cmd.prevY;
            }

            // new x
            if (cmd.x === undefined || isNaN(cmd.x)) {
                x = prevX;
            } else {
                x = cmd.x;
            }

            // new y
            if (cmd.y === undefined || isNaN(cmd.y)) {
                y = prevY;
            } else {
                y = cmd.y;
            }

            // current tool
            var tool = cmd.tool || 0;

            if (!cmd.extrude && !cmd.noMove) {
                // neither extrusion nor move
                if (cmd.retract == -1) {
                    // retract => draw dot if configured to do so
                    if (renderOptions["showRetracts"]) {
                        strokePathIfNeeded("fill");
                        ctx.fillStyle = getColorRetractForTool(tool);
                        ctx.strokeStyle = ctx.fillStyle;
                        drawTriangle(prevX, prevY, sizeRetractSpot, true);
                    }
                }

                strokePathIfNeeded("move", getColorMoveForTool(tool));
                if(renderOptions["showMoves"]){
                    // move => draw line from (prevX, prevY) to (x, y) in move color
                    ctx.lineWidth = lineWidthFactor;
                    ctx.lineTo(x,y);
                }
            } else if(cmd.extrude) {
                if (cmd.retract == 0) {
                    // no retraction => real extrusion move, use tool color to draw line
                    strokePathIfNeeded("extrude", getColorLineForTool(tool));
                    ctx.lineWidth = renderOptions['extrusionWidth'] * lineWidthFactor;
                    if (cmd.direction !== undefined && cmd.direction != 0){
                        var di = cmd.i;
                        var dj = cmd.j;
                        var centerX = prevX+di;
                        var centerY = prevY+dj;
                        var startAngle = Math.atan2(prevY-centerY, prevX - centerX);
                        var endAngle = Math.atan2(y - centerY, x - centerX);
                        var radius=Math.sqrt(di*di+dj*dj);
                        ctx.arc(centerX,centerY,radius,startAngle,endAngle,cmd.direction<0); // Y-axis is inverted so direction is also inverted
                    } else {
                        ctx.lineTo(x,y);
                    }
                } else {
                    // we were previously retracting, now we are restarting => draw dot if configured to do so
                    if (renderOptions["showRetracts"]) {
                        strokePathIfNeeded("fill");
                        ctx.fillStyle = getColorRestartForTool(tool);
                        ctx.strokeStyle = ctx.fillStyle;
                        drawTriangle(prevX, prevY, sizeRetractSpot, false);
                    }
                }
            }

            // set new (prevX, prevY)
            prevX = x;
            prevY = y;
        }
        
        if (prevPathType != "fill") {
            ctx.stroke();
        }

        if (renderOptions["showHead"]) {
            var sizeHeadSpot = renderOptions["sizeHeadSpot"] * lineWidthFactor + lineWidthFactor / 2;
            var shade = tool * 0.15;
            ctx.fillStyle = pusher.color(renderOptions["colorHead"]).shade(shade).alpha(alpha).html();
            ctx.beginPath();
            ctx.arc(prevX, prevY, sizeHeadSpot, 0, Math.PI*2, true);
            ctx.fill();
        }
    };

    var applyOffsets = function() {
        var canvasCenter;

        // determine bed and model offsets
        if (ctx) ctx.translate(-offsetModelX, -offsetModelY);
        if (renderOptions["centerViewport"] || renderOptions["zoomInOnModel"]) {
            canvasCenter = ctx.transformedPoint(canvas.width / 2, canvas.height / 2);
            if (modelInfo) {
                offsetModelX = canvasCenter.x - (modelInfo.boundingBox.minX + modelInfo.boundingBox.maxX) / 2;
                offsetModelY = canvasCenter.y - (modelInfo.boundingBox.minY + modelInfo.boundingBox.maxY) / 2;
            } else {
                offsetModelX = 0;
                offsetModelY = 0;
            }
            offsetBedX = 0;
            offsetBedY = 0;
        } else if (modelInfo && renderOptions["moveModel"]) {
            offsetModelX = (renderOptions["bed"]["x"] / 2 - (modelInfo.boundingBox.minX + modelInfo.boundingBox.maxX) / 2);
            offsetModelY = (renderOptions["bed"]["y"] / 2 - (modelInfo.boundingBox.minY + modelInfo.boundingBox.maxY) / 2);
            offsetBedX = -1 * (renderOptions["bed"]["x"] / 2 - (modelInfo.boundingBox.minX + modelInfo.boundingBox.maxX) / 2);
            offsetBedY = -1 * (renderOptions["bed"]["y"] / 2 - (modelInfo.boundingBox.minY + modelInfo.boundingBox.maxY) / 2);
        } else if (renderOptions["bed"]["circular"] || renderOptions["bed"]["centeredOrigin"]) {
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

    var applyZoom = function() {
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

        if (modelInfo && renderOptions["zoomInOnModel"]) {
            // if we need to zoom in on model, scale factor is calculated by longer side of object in relation to that axis of canvas
            var width = modelInfo.boundingBox.maxX - modelInfo.boundingBox.minX;
            var length = modelInfo.boundingBox.maxY - modelInfo.boundingBox.minY;

            var scaleF = width > length ? (canvas.width - 10) / width : (canvas.height - 10) / length;
            if (transform.a && transform.d) {
                scaleX = scaleF / transform.a * (renderOptions["invertAxes"]["x"] ? -1 : 1);
                scaleY = scaleF / transform.d * (renderOptions["invertAxes"]["y"] ? 1 : -1);
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

            // Ratio of bed to canvas viewport
            var viewportRatio = Math.min((canvas.width - 10) / bedWidth, (canvas.height - 10) / bedHeight);

            // Apply initial translation to center the bed in the viewport
            var translationX, translationY;
            if (renderOptions["bed"]["circular"]) {
                translationX = canvas.width / 2;
                translationY = canvas.height / 2;
            } else {
                translationX = (canvas.width - bedWidth * viewportRatio) / 2;
                translationY = bedHeight * viewportRatio + (canvas.height - bedHeight * viewportRatio) / 2;
            }
            ctx.translate(translationX, -translationY);

            ctx.scale(viewportRatio, viewportRatio);
            
            offsetModelX = 0;
            offsetModelY = 0;
            offsetBedX = 0;
            offsetBedY = 0;

            // Scaling to apply to move lines and extrusion/retraction markers
            lineWidthFactor = 1 / viewportRatio;
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
                if ($.inArray(opt, ["moveModel", "centerViewport", "zoomInOnModel", "bed", "invertAxes", "onViewportChange"]) > -1) {
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
            
            layerNumStore = layerNum;
            progressStore.from = fromProgress;
            progressStore.to = toProgress;

            reRender();
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
            modelInfo = undefined;

            this.doRender([], 0);
        },
        doRender: function(mdl, layerNum){
            model = mdl;
            modelInfo = undefined;

            prevX = 0;
            prevY = 0;
            if (!initialized) this.init();

            var toProgress = 1;
            if (model && model.length) {
                modelInfo = GCODE.gCodeReader.getModelInfo();
                speeds = modelInfo.speeds;
                speedsByLayer = modelInfo.speedsByLayer;
                if (model[layerNum]) {
                    toProgress = model[layerNum].length;
                }
            }

            applyInversion();
            applyOffsets();
            applyZoom();

            this.render(layerNum, 0, toProgress);
        },
        refresh: function(layerNum) {
            if (layerNum === undefined) layerNum = layerNumStore;
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
