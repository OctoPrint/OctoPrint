(function (global, factory) {
    if (typeof define === "function" && define.amd) {
        define(["OctoPrint"], factory);
    } else {
        factory(window.OctoPrint);
    }
})(window || this, function(OctoPrint) {
    var url = "api/slicing";

    var slicerUrl = function(slicer) {
        return url + "/" + slicer;
    };

    var profileUrl = function(slicer, profileId) {
        return slicerUrl(slicer) + "/profiles/" + profileId;
    };

    OctoPrint.slicing = {
        listAllSlicersAndProfiles: function(opts) {
            return OctoPrint.get(url, opts);
        },

        listProfilesForSlicer: function(slicer, opts) {
            return OctoPrint.get(slicerUrl(slicer) + "/profiles", opts);
        },

        getProfileForSlicer: function(slicer, profileId, opts) {
            return OctoPrint.get(profileUrl(slicer, profileId), opts);
        },

        addProfileForSlicer: function(slicer, profileId, profile, opts) {
            profile = profile || {};
            return OctoPrint.putJson(profileUrl(slicer, profileId), profile, opts);
        },

        updateProfileForSlicer: function(slicer, profileId, profile, opts) {
            profile = profile || {};
            return OctoPrint.patchJson(profileUrl(slicer, profileId), profile, opts);
        },

        deleteProfileForSlicer: function(slicer, profileId, opts) {
            return OctoPrint.delete(profileUrl(slicer, profileId), opts);
        }
    }
});
