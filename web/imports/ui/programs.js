import './programs.html';

import { Programs } from '../api/programs.js';
import $ from 'jquery';


// subscribe to programs stream
Template.programs.onCreated(function onCreated() {
    Meteor.subscribe('programs');
});

Template.programAction.helpers({
    isCurrentUser(userId) {
	return userId === Meteor.userId();
    },
});

// access programs
Template.programs.helpers({
    programs() {
	return Programs.find({ owner: Meteor.userId()});
    },
    settings() {
	return {
	    collection: Programs,
	    showRowCount: true,
	    showNavigationRowsPerPage: false,
	    noDataTmpl: Template.noPrograms,
	    fields: [
		{key: 'name',
		 label: 'Name'},
		{key: 'executor',
		 label: 'Execution'},
		{key: 'createdAt',
		 label: 'Created'},
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
		 tmpl: Template.programAction
		}
	    ]
      
	};
    }
});

// event handlers
Template.programs.events({
    // submitting new programs
    'submit .new-program'(event) {

	// prevent default browser
	event.preventDefault();

	// clear 'success' formatting from form
	$('.new-program').find('.form-group').removeClass('has-success');

	// get value from form
	const target = event.target;
	const name = target.name.value;
	const executor = target.executor.value;

	// submit new program
	Meteor.call('programs.insert', name, executor);

	// reset form
	$('.new-program')[0].reset();
    },

    // on press of the delete button
    'click .reactive-table tbody tr': function (event) {
	event.preventDefault();
	// checks if the actual clicked element has the class `delete`
	if (event.target.className.includes('action-delete')) {

	    // find the program
	    const program = Programs.findOne(this._id);

	    // we do not allow deleting the General program
	    if (program.name == 'General') {
		CoffeeAlerts.error('You cannot delete the "General" program');
		return;
	    }
	    else {
		// delete program
		Meteor.call('programs.remove', this._id);
	    }
	} else if (event.target.className.includes('action-completed')) {
	    // mark program completed
	    Meteor.call('programs.setCompleted', this._id, ! this.completed);
	}
    }
})

// build rules for form validation
Template.programs.onRendered(function() {
    $( '.new-program' ).validate({
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
	    name: {
		required: true,
		minlength: 4,
		maxlength: 32},
	    executor: {
		required: true}

	},
	messages: {
	    name: {
		required: "You have to give your observing program a name...",
		minlength: "Please make the name longer than 4 characters",
		maxlength: "verbosity may be king, but a name shorted than 32 characters would be appreciated"}
	}
    });
});
