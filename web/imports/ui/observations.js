import './observations.html';

import { Meteor } from 'meteor/meteor';
import { ReactiveDict } from 'meteor/reactive-dict';
import { Session } from 'meteor/session';
import { Observations } from '../api/observations.js';
import { Programs } from '../api/programs.js';
import $ from 'jquery';

// global variable to store dSS preview
aladin = null;


// load sky preview
Template.newObservation.onCreated(function onCreated() {

    // aladin is disabled until HTTPS is fixed
    // $.getScript("https://aladin.u-strasbg.fr/AladinLite/api/v2/latest/aladin.min.js", function() {
    //     aladin = A.aladin('#aladin-lite-div', {survey: "P/DSS2/color",
    //                                            fov: (26/60),
    //                                            showLayersControl: false,
    //                                            showShareControl: false,
    //                                            showZoomControl: false,
    //                                            showGotoControl: false,
    //                                            showReticle: false,
    //                                            showFrame: false});

    // });

});

// subscribe to program stream
Template.observations.onCreated(function onCreated() {
    Meteor.subscribe('observations');
    Meteor.subscribe('programs');
});

// subscribe to program stream
Template.newObservationForm.onCreated(function onCreated() {
    Meteor.subscribe('programs');

    // compute the current observation time and update the Session variable
    Meteor.call('observations.totalAvailableTime', function(error, total) {
        Session.set('totalAvailableTime', total);
    });

    // reactive dict to store observation properties
    if (!this.obsProperties) {
        this.obsProperties = new ReactiveDict();
        this.obsProperties.set('expcount', 0); // exp count
        this.obsProperties.set('exptime',  0); // exp time in seconds
        this.obsProperties.set('numfilters', 1); // total number of filters
        this.obsProperties.set('xframe', 1); // number of x-frames in mosaic
        this.obsProperties.set('yframe', 1); // number of y-frames in mosaic
    };
});

// Template.observationAction.onRendered(function() {
//     var clipboard = new Clipboard('.copy-link');
// });

// helpers for the new observation form
Template.newObservationForm.helpers({
    // return all programs owned by the user, or owned by no-one (public programs)
    programs() {
        return Programs.find({ '$or': [{owner: Meteor.userId()}, {owner: null}, {'sharedWith': Meteor.userId()}]});
    },
    // total observation time string ; in seconds if less than 60s,
    // in minutes if less than 60 minutes, in hours otherwise
    totalObservationTime() {
        obsProperties = Template.instance().obsProperties;
        if (obsProperties) {
            expcount = obsProperties.get('expcount');
            exptime = obsProperties.get('exptime');
            numfilters = obsProperties.get('numfilters');
            xframe = obsProperties.get('xframe');
            yframe = obsProperties.get('yframe');

            totalTime = expcount*exptime*(numfilters)*xframe*yframe;

            if (totalTime <= 900) { // return time in seconds
                time = parseFloat(totalTime).toFixed(0);
                return time + " s";
            }  else if (totalTime <= 60*60) { // return time in minutes
                time = parseFloat(totalTime/60).toFixed(1);
                return time + " mins";
            }
            else { // return time in hours
                time = parseFloat(totalTime/(60*60)).toFixed(1);
                return time + " hours";
            }
        } else {
            return "0 s";
        }
    },
    totalAvailableTime() {
        availableTime =  Session.get('totalAvailableTime');

        if (availableTime <= 900) { // return time in seconds
            time = parseFloat(availableTime).toFixed(0);
            return time + " s";
        }  else if (availableTime <= 60*60) { // return time in minutes
            time = parseFloat(availableTime/60).toFixed(1);
            return time + " mins";
        }
        else { // return time in hours
            time = parseFloat(availableTime/(60*60)).toFixed(1);
            return time + " hours";
        }
    },

    // return whether the current program name equals the argument
    isEqual() {
        program = arguments[0]; // program name
        if (program) {
            for (var i = 1; i < arguments.length; i++) {
                if (program.name == arguments[i]) {
                    return true;
                }
            }
        }
        return false;
    },
});

// event handlers
Template.newObservationForm.events({
    'blur #target'(event) {
        CoffeeAlerts.clearSeen();

        // load visiblity curves
        HTTP.get('https://sirius.stoneedgeobservatory.com:8179/visibility/'+event.target.value,
                 function (error, response) {
                     if (error) {
                         console.log(error);
                     } else {
                         // set src of visibility plot to content of response
                         $("#visibility_plot").attr('src','data:image/png;base64,'+response.content);
                     }
                 });

        // load target preview
        HTTP.get('https://sirius.stoneedgeobservatory.com:8179/preview/'+event.target.value,
                 function (error, response) {
                     if (error) {
                         console.log(error);
                     } else {
                         // set src of visibility plot to content of response
                         $("#target_preview").attr('src','data:image/png;base64,'+response.content);
                     }
                 });

        // point Aladin preview at object
        // if (event.target.value) {
        //     if (aladin) {
        //  aladin.gotoObject(event.target.value);
        //     }
        // }

        event.preventDefault();
    },
    'submit .new-observation'(event, instance) {

        // prevent default browser
        event.preventDefault();

        // clear 'success' formattingn from form
        $('.new-observation').find('.form-group').removeClass('has-success');

        // get value from form
        const target = event.target;
        const progId = target.program.value;
        const target_name = target.target.value;
        const exptime = target.exptime.value;
        const expcount = target.expcount.value;
        const binning = target.binning.value;
        const lunar = target.lunar.value;
        const airmass = target.airmass.value;
        const offset_ra = target.offset_ra.value;
        const offset_dec = target.offset_dec.value;
        const xframe = target.x_frame.value;
        const yframe = target.y_frame.value;

        // build filter list
        const filterNames = ['filter_clear', 'filter_dark', 'filter_u', 'filter_g',
                             'filter_r', 'filter_i', 'filter_z',
                             'filter_ha'];
        var filters = [];
        for (var i = 0; i < filterNames.length; i++) {
            if (target[filterNames[i]].checked) {
                if (filterNames[i].split('_')[1] == 'ha') {
                    filters.push('h-alpha');
                }
                else if (filterNames[i].split('_')[1] == 'clear') {
                    filters.push('clear');
                }
                else if (filterNames[i].split('_')[1] == 'dark') {
                    filters.push('dark');
                }
                else {
                    filters.push(filterNames[i].split('_')[1]+'-band');
                }
            }
        }

        // check that at least one filter is selected
        if (filters.length == 0) {
            CoffeeAlerts.error('Your observation needs at least one filter.');
            return;
        }

        // check the time allowed is sufficient
        availableTime =  Session.get('totalAvailableTime');
        if (availableTime < Number(exptime)*Number(expcount)*filters.length) {
            CoffeeAlerts.error('You do not have enough credits to submit this observation');
            return;
        }

        // optional parameters
        options = {'lunar': lunar, 'airmass': airmass,
                   'offset_ra': offset_ra, 'offset_dec': offset_dec,
                   'xframe': xframe, 'yframe': yframe};

        // submit new observation
        Meteor.call('observations.insert', progId, target_name, exptime, expcount, binning, filters, options);

        // update the users available time
        Meteor.call('observations.totalAvailableTime', function(error, total) {
            Session.set('totalAvailableTime', total);
        });

        // reset the observation properties
        instance.obsProperties.set('expcount', 0); // exp count
        instance.obsProperties.set('exptime',  0); // exp time in seconds
        instance.obsProperties.set('numfilters', 1); // total number of filters
        instance.obsProperties.set('xframe', 1); // number of x-frames in mosaic
        instance.obsProperties.set('yframe', 1); // number of y-frames in mosaic

        // alert the user
        CoffeeAlerts.success('Your observation has successfully been added');

        // reset form
        $('.new-observation')[0].reset();

    },
    // the below handlers update the ReactiveDict to calculate total observation time
    'blur #exptime'(event, instance) {
        if (instance.obsProperties) {
            instance.obsProperties.set('exptime', event.target.value);
        }
        event.preventDefault();
        CoffeeAlerts.clearSeen();
    },
    'blur #expcount'(event, instance) {
        if (instance.obsProperties) {
            instance.obsProperties.set('expcount', event.target.value);
        }
        event.preventDefault();
        CoffeeAlerts.clearSeen();
    },
    'blur #x_frame'(event, instance) {
        if (instance.obsProperties) {
            instance.obsProperties.set('xframe', event.target.value);
        }
        event.preventDefault();
        CoffeeAlerts.clearSeen();
    },
    'blur #y_frame'(event, instance) {
        if (instance.obsProperties) {
            instance.obsProperties.set('yframe', event.target.value);
        }
        event.preventDefault();
        CoffeeAlerts.clearSeen();
    },
    'change .filter'(event, instance) {
        if (instance.obsProperties) {
            const count = instance.obsProperties.get('numfilters');
            if (event.target.checked) {
                instance.obsProperties.set('numfilters', count+1);
            } else {
                instance.obsProperties.set('numfilters', count-1);
            }
        }
        event.preventDefault();
        CoffeeAlerts.clearSeen();
    }
});

// build rules for form validation
Template.newObservation.onRendered(function() {
    $( '.new-observation' ).validate({
        errorClass: 'text-danger',
        errorElement: 'p',
        highlight: function(element, errorClass) {
            $(element.form).find('#form-'+element.id).removeClass('has-success');
            $(element.form).find('#form-'+element.id).addClass('has-error');
        },
        unhighlight: function(element, errorClass) {
            $(element.form).find('#form-'+element.id).removeClass('has-error');
            $(element.form).find('#form-'+element.id).addClass('has-success');
        },
        rules: {
            program: {
                required: true,
            },
            target: {
                required: true,
                minlength: 2,
                maxlength: 18
            },
            exptime: {
                required: true,
                min: 0.1,
                max: 900
            },
            expcount: {
                required: true,
                min:1,
                max:100,
                digits: true
            },
            binning: {
                required: true,
                min:1,
                max: 8,
                digits: true
            }
        },
        messages: {
            target: {
                required: "Please enter a target for your observation!",
                minlength: "That doesn't look like a real target...",
                maxlength: "That's not a valid target name - please enter an identifier i.e. 'M31', 'NGC6946'"
            },
            exptime: {
                required: "We need to know how long you want to expose for!",
                min: "That exposure time is too short; minimum exposure-time is 0.1s",
                max: "That exposure time is waaaaay too long; most things will be saturated"
            },
            expcount: {
                required: "Please enter a valid integer nmber of exposure counts",
                min: "You need to take atleast 1 exposure!",
                max: "That is an excessive number of exposures; please make this less than 100",
                digits: "This needs to be an integer - we can't have any half exposures can we?"
            },
            binning: {
                required: "You need to set a binning - we recommend 1 or 2",
                min: "CCD Binning needs to be greated than 1!",
                max: "A CCD binning over 8 is excessive - please lower the binning",
                digits: "This needs to be an integer!"
            }
        },
    });
});


// access observations
Template.observations.helpers({
    observations() {
        return Observations.find({ owner: Meteor.userId()});
    },
    settings() {
        return {
            showRowCount: true,
            showNavigationRowsPerPage: false,
            noDataTmpl: Template.noObservations,
            fields: [
                {key: 'program',
                 label: 'Program',
                 fn: function (value, object, key) {
                     program = Programs.findOne(value);
                     if (program) {
                         return program.name;
                     }
                 }},
                {key: 'target',
                 label: 'Target'},
                {key: 'exposure_time',
                 label: 'Exposure Time (s)'},
                {key: 'exposure_count',
                 label: 'Exposure Count'},
                {key: 'filters',
                 label: 'Filters',
                 fn: function (value, object, key) {
                     return value.join(', ');
                 }},
                {key: 'binning',
                 label: 'Binning'},
                // {key: 'submitDate',
                //  label: 'Date Submitted'},
                {key: 'completed',
                 label: 'Completed',
                 fn: function (value, object, key) {
                     if (value === true) {
                         return "Yes";
                     } else {
                         return "No";
                     }
                 }
                },
                {label: '',
                 tmpl: Template.observationAction
                }
            ]
        };
    }
});

Template.observations.events({
    // on press of the action button
    'click .reactive-table tbody tr': function (event) {
        event.preventDefault();
        // checks if the actual clicked element has the class `delete`
        if (event.target.className.includes('action-delete')) {
            // delete program
            Meteor.call('observations.remove', this._id);
        } else if (event.target.className.includes('action-completed')) {
            // mark program completed
            Meteor.call('observations.setCompleted', this._id, ! this.completed);
        }
    }
});
