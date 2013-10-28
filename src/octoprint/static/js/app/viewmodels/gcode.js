function GcodeViewModel(loginStateViewModel) {
    var self = this;

    self.loginState = loginStateViewModel;

    self.loadedFilename = undefined;
    self.loadedFileMTime = undefined;
    self.status = 'idle';
    self.enabled = false;

    self.errorCount = 0;

    self.initialize = function(){
        self.enabled = true;
        GCODE.ui.initHandlers();
    }

    self.loadFile = function(filename, mtime){
        if (self.status == 'idle' && self.errorCount < 3) {
            self.status = 'request';
            $.ajax({
                url: BASEURL + "downloads/gcode/" + filename,
                data: { "mtime": mtime },
                type: "GET",
                success: function(response, rstatus) {
                    if(rstatus === 'success'){
                        self.showGCodeViewer(response, rstatus);
                        self.loadedFilename=filename;
                        self.loadedFileMTime=mtime;
                        self.status = 'idle';
                    }
                },
                error: function() {
                    self.status = 'idle';
                    self.errorCount++;
                }
            })
        }
    }

    self.showGCodeViewer = function(response, rstatus) {
        var par = {};
        par.target = {};
        par.target.result = response;
        GCODE.gCodeReader.loadFile(par);
    }

    self.fromHistoryData = function(data) {
        self._processData(data);
    }

    self.fromCurrentData = function(data) {
        self._processData(data);
    }

    self._processData = function(data) {
        if (!self.enabled) return;
        if (!data.job.filename) return;

        if(self.loadedFilename && self.loadedFilename == data.job.filename &&
            self.loadedFileMTime == data.job.mtime) {
            if (data.state.flags && (data.state.flags.printing || data.state.flags.paused)) {
                var cmdIndex = GCODE.gCodeReader.getCmdIndexForPercentage(data.progress.progress * 100);
                if(cmdIndex){
                    GCODE.renderer.render(cmdIndex.layer, 0, cmdIndex.cmd);
                    GCODE.ui.updateLayerInfo(cmdIndex.layer);
                }
            }
            self.errorCount = 0
        } else if (data.job.filename) {
            self.loadFile(data.job.filename, data.job.mtime);
        }
    }

}
