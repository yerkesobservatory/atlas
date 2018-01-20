import './programs.html';

import { Programs } from '../api/programs.js';
import { Observations } from '../api/observations.js';
import $ from 'jquery';


// subscribe to programs stream
Template.programs.onCreated(function onCreated() {
    Meteor.subscribe('programs');
});

// subscribe to programs stream
Template.programDetailsModal.onCreated(function onCreated() {
    Meteor.subscribe('observations');
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
            showRowCount: true,
	    multiColumnSort: false,
	    rowsPerPage: 10,
            showNavigationRowsPerPage: false,
	    showFilter: false,
            // noDataTmpl: Template.noPrograms,
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

// access programs
Template.programDetailsModal.helpers({
    numPending(name) {
	if (name) {
	    const observations = Programs.findOne({'name': name}).observations;
	    if (observations) {
		return Observations.find({'_id': {"$in": observations},
					  'completed': false}).count();
	    }
	}
    },
    numCompleted(name) {
	if (name) {
	    const observations = Programs.findOne({'name': name}).observations;
	    if (observations) {
		return Observations.find({'_id': {"$in": observations},
					  'completed': true}).count();
	    }
	}
    },
    owner(name) {
	if (name) {
	    program = Programs.findOne({'name': name});
	    if (program.owner == null) {
		return "Public";
	    }
	    else {
		return program.owner;
	    }
	}
    },
    settings() {
	return {
	    showRowCount: true,
	    showNavigation: 'never',
	    multiColumnSort: false,
	    showFilter: false,
	    showNavigationRowsPerPage: false,
	    // noDataTmpl: Template.noPrograms,
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
    'click #button_dso'(event, instance) {
	event.preventDefault();
        Modal.show('programDetailsModal', Programs.findOne({'name': 'General'}));
    },
    'click #button_asteroid'(event, instance) {
	event.preventDefault();
        Modal.show('programDetailsModal', Programs.findOne({'name': 'Asteroids'}));
    },
    'click #button_variable'(event, instance) {
	event.preventDefault();
        Modal.show('programDetailsModal', Programs.findOne({'name': 'Variable Stars'}));
    },
    'click #button_solar'(event, instance) {
	event.preventDefault();
        Modal.show('programDetailsModal', Programs.findOne({'name': 'Solar System'}));
    },
    'click #new_program_div'(event, instance) {
    	event.preventDefault();
    	Modal.show('newProgramModal');
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

Template.newProgramModal.events({
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

	// close the modal
	Modal.hide();
    },
});

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
                minlength: 3,
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
