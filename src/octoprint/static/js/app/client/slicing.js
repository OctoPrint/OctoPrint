OctoPrint.slicing = (function($, _) {
    var exports = {};

    var url = "api/slicing";

    var getProfileUrl = function(slicer, profileId) {
        return url + "/" + slicer + "/profiles/" + profileId;
    };

    exports.listAllSlicersAndProfiles = function(opts) {
        return OctoPrint.get(url, opts);
    };

    exports.listProfilesForSlicer = function(slicer, opts) {
        var slicerUrl = url + "/" + slicer + "/profiles";
        return OctoPrint.get(slicerUrl, opts);
    };

    exports.getProfileForSlicer = function(slicer, profileId, opts) {
        return OctoPrint.get(getProfileUrl(slicer, profileId), opts);
    };

    exports.addProfileForSlicer = function(slicer, profileId, profile, opts) {
        profile = profile || {};
        return OctoPrint.putJson(getProfileUrl(slicer, profileId), profile, opts);
    };

    exports.updateProfileForSlicer = function(slicer, profileId, profile, opts) {
        profile = profile || {};
        return OctoPrint.patchJson(getProfileUrl(slicer, profileId), profile, opts);
    };

    exports.deleteProfileForSlicer = function(slicer, profileId, opts) {
        return OctoPrint.delete(getProfileUrl(slicer, profileId), opts);
    };

    return exports;
})($, _);
