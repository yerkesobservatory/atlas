import './affiliations.html';

import { Affiliations } from '../api/users.js';

// subscribe to users
Template.adminAffiliations.onCreated(function onCreated() {
    Meteor.subscribe('affiliations');
});

Template.adminAffiliations.helpers({
    settings() {
	return {
	    collection: Affiliations,
	    showRowCount: true,
	    showNavigationRowsPerPage: true,
	    showFilter: false,
	    noDataTmpl: Template.noAffiliations, 
	    fields: [
		{key: 'name',
		 label: 'Name'},
		{label: '',
		 fn: function(value) {
		     return new Spacebars.SafeString('<a href="#" class="btn btn-danger delete">Delete</a>');
		 }
		}
	    ]
	};
    }
});

// event handlers
Template.adminAffiliations.events({
    // submitting new programs
    'submit .new-affiliation'(event) {

	// prevent default browser
	event.preventDefault();

	// clear 'success' formatting from form
	$('.new-affiliation').find('.form-group').removeClass('has-success');

	// get value from form
	const target = event.target;
	const name = target.affiliation.value;

	// submit new program
	Meteor.call('affiliations.insert', name);

	// reset form
	$('.new-affiliation')[0].reset();
    },

    // on press of the delete button
    'click .reactive-table tbody tr': function (event) {
	event.preventDefault();
	// checks if the actual clicked element has the class `delete`
	if (event.target.className.includes('delete')) {
	    // delete observation
	    Meteor.call('affiliations.remove', this._id);
	}
    }
});
