import './admin.html';
import './affiliations.html';

import './users.js';
import './affiliations.js';

import { Observations } from '../api/observations.js';
import { Programs } from '../api/programs.js';

// subscribe to users
Template.adminObservations.onCreated(function onCreated() {
    Meteor.subscribe('observations');
    Meteor.subscribe('programs');
});

// access observations
Template.adminObservations.helpers({
    observations() {
	return Observations.find();
    }, 
    settings() {
	return {
	    collection: Observations,
	    showRowCount: true,
	    showNavigationRowsPerPage: false,
	    noDataTmpl: Template.noObservations, 
	    fields: [
		{key: 'email',
		 label: 'User',
		},
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


Template.adminObservations.events({
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
