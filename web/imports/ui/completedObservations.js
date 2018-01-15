import './completedObservations.html';
import { Meteor } from 'meteor/meteor';
import { Observations } from '../api/observations.js';
import { Programs } from '../api/programs.js';
import $ from 'jquery';

// subscribe to stream
Template.completedObservations.onCreated(function onCreated() {
    Meteor.subscribe('observations');
});

Template.completedObservationAction.onRendered(function() {
    var clipboard = new Clipboard('.copy-link');
});

// subscribe to stream
Template.newObservation.onCreated(function onCreated() {
    Meteor.subscribe('programs');
});


// access observations
Template.completedObservations.helpers({
    completedObservations() {
	return Observations.find({ owner: Meteor.userId()});
    },
    settings() {
	return {
	    collection: Observations,
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
		 tmpl: Template.completedObservationAction
		}
	    ]
	};
    }
});

Template.completedObservations.events({
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
