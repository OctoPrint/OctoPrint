(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrintClient"], factory);
    } else {
        factory(global.OctoPrintClient);
    }
})(this, function(OctoPrintClient) {
    var url = "api/slicing";

    var slicerUrl = function(slicer) {
        return url + "/" + slicer;
    };

    var profileUrl = function(slicer, profileId) {
        return slicerUrl(slicer) + "/profiles/" + profileId;
    };

    var OctoPrintSlicingClient = function(base) {
        this.base = base;
    };

    OctoPrintSlicingClient.prototype.listAllSlicersAndProfiles = function(opts) {
        return this.base.get(url, opts);
    };

    OctoPrintSlicingClient.prototype.listProfilesForSlicer = function(slicer, opts) {
        return this.base.get(slicerUrl(slicer) + "/profiles", opts);
    };

    OctoPrintSlicingClient.prototype.getProfileForSlicer = function(slicer, profileId, opts) {
        return this.base.get(profileUrl(slicer, profileId), opts);
    };

    OctoPrintSlicingClient.prototype.addProfileForSlicer = function(slicer, profileId, profile, opts) {
        profile = profile || {};
        return this.base.putJson(profileUrl(slicer, profileId), profile, opts);
    };

    OctoPrintSlicingClient.prototype.updateProfileForSlicer = function(slicer, profileId, profile, opts) {
        profile = profile || {};
        return this.base.patchJson(profileUrl(slicer, profileId), profile, opts);
    };

    OctoPrintSlicingClient.prototype.deleteProfileForSlicer = function(slicer, profileId, opts) {
        return this.base.delete(profileUrl(slicer, profileId), opts);
    };

    OctoPrintClient.registerComponent("slicing", OctoPrintSlicingClient);
    return OctoPrintSlicingClient;
});
