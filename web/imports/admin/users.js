import './users.html';

import { Programs } from '../api/programs.js';
import { Affiliations } from '../api/users.js';

// subscribe to users
Template.adminUsers.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('affiliations');
});

Template.userAction.helpers({
    isAdmin(userId) {
	return Roles.userIsInRole(userId, 'admin');
    },
});


Template.adminUsers.helpers({
        affiliations() {
	return Affiliations.find({});
    },
    settings() {
	return {
	    collection: Meteor.users,
	    showRowCount: true,
	    showNavigationRowsPerPage: false,
	    fields: [
		{key: '',
		 label: 'Email',
		 fn: function (value, object, key) {
		     return object.emails[0].address;
		 }},
		// {key: 'firstName',
		//  label: 'First Name'},
		// {key: 'lastName',
		//  label: 'Last Name'},
		{key: 'profile.affiliation',
		 label: 'Affiliation', 
		},
		{key: 'profile.minor',
		 label: 'Under 18?',
		 fn: function (value, object, key) {
		     if (value === true) {
			 return "Yes";
		     } else {
			 return "No";
		     }
		 }
		},
            {key: '_id',
             label: 'ID', 
            }, 
		{key: '_id',
		 label: 'Role',
		 fn: function (value, object, key) {
		     // console.log(value);
		     // console.log(Roles.userIsInRole(value, 'users'))
		     // if (Roles.userIsInRole(value, 'admins')) {
		     // 	 return 'Admin';
		     // }
		     // else if (Roles.userIsInRole(value, 'users')) {
		     // 	 return 'User';
		     // } else {
		     // 	     return 'Unknown';
		     // }
		 }
		}, 
		{label: '',
		 tmpl: Template.userAction
		}
	    ]
	}
    }
});


Template.adminUsers.events({
    'submit .new-user'(event) {

	// prevent default submission
	event.preventDefault();

	// clear 'success' formatting from form
	$('.new-user').find('.form-group').removeClass('has-success');

	// extract values
	const target = event.target;
	const email = target.email.value;
	const affiliation = target.affiliation.value;
	const minor = target.minor.checked;

	// create new user
	const profile =  {
		affiliation: affiliation,
		minor: minor,
	}

	// insert user
	Meteor.call('users.insert', email, profile);

	// reset form
	$('.new-user')[0].reset();

    }, 
    
    // on press of the delete button
    'click .reactive-table tbody tr': function (event) {
	event.preventDefault();
	// checks if the actual clicked element has the class `delete`
	if (event.target.className.includes('action-delete')) {
	    // delete user
	    Meteor.call('users.remove', this._id);
	} else if (event.target.className.includes('action-admin')) {
	    // toggle admin state
	    Meteor.call('users.toggleAdmin', this._id);
	}
    }
});

// build rules for form validation
Template.adminUsers.onRendered(function() {
    $( '.new-user' ).validate({
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
	    email: {
		required: true,
		minlength: 5,
		maxlength: 48},
	    affiliation: {
		required: true,
		minlength: 5,
		maxlength: 32
	    }, 
	},
	messages: {
	    email: {
		required: "Every user needs an email address!",
	    }
	}
    });
});
