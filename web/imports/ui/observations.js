import './observations.html';

import { Meteor } from 'meteor/meteor';
import { Observations } from '../api/observations.js';
import { Programs } from '../api/programs.js';
import $ from 'jquery';

// subscribe to stream
Template.observations.onCreated(function onCreated() {
    Meteor.subscribe('observations');
});

// subscribe to stream
Template.newObservation.onCreated(function onCreated() {
    Meteor.subscribe('programs');
});

// access observations
Template.observations.helpers({
    observations() {
	return Observations.find({ owner: Meteor.userId()});
    }, 
    settings() {
	return {
	    collection: Observations,
	    showRowCount: true,
	    showNavigationRowsPerPage: false,
	    noDataTmpl: Template.noObservations, 
	    fields: [
		{key: 'programId',
		 label: 'Program',
		 fn: function (value, object, key) {
		     return Programs.find(value).fetch()[0].name;
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

// subscribe to observations
Template.newObservation.helpers({
    programs() {
	return Programs.find({ owner: Meteor.userId() });
    }
});

// event handlers
Template.observations.events({
    'submit .new-observation'(event) {

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

	// build filter list
	const filterNames = ['filter_clear', 'filter_u', 'filter_g',
			     'filter_r', 'filter_i', 'filter_z',
			     'filter_ha'];
	var filters = [];
	for (var i = 0; i < filterNames.length; i++) {
	    if (target[filterNames[i]].checked) {
		filters.push(filterNames[i].split('_')[1]);
	    }
	}
	
	// submit new observation
	Meteor.call('observations.insert', progId, target_name, exptime, expcount, binning, filters);
	
	// reset form
	$('.new-observation')[0].reset();

    },
});

// build rules for form validation
Template.observations.onRendered(function() {
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
