import './users.html';
// import '../ui/profile.html';

import { Programs } from '../api/programs.js';
import { Groups } from '../api/groups.js';
import $ from 'jquery';

// subscribe to users
Template.adminUsers.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});

Template.userAction.helpers({
    isAdmin(userId) {
        return Roles.userIsInRole(userId, 'admin');
    }
});


Template.adminUsers.helpers({
    groups() {
        return Groups.find({});
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
                     if (object.emails[0].verified) {
                         return object.emails[0].address;
                     }
                     else {
                         return Spacebars.SafeString('<p style="color:red">'+object.emails[0].address+'</p>');
                     }
                 }},
                {key: 'profile.firstName',
                 label: 'First'},
                {key: 'profile.lastName',
                 label: 'Last'},
                {key: 'group',
                 label: 'Group'},
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
                 label: 'ID'
                },
                {key: 'roles',
                 label: 'Roles',
                 fn: function (value, object, key) {
                     if (Roles.userIsInRole(object, 'admin')){
                        return 'admin';
                     }
                     return 'user';
                 }
                },
                {label: '',
                 tmpl: Template.userAction
                }
            ]
        };
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
        const name = target.name.value.split(' ');
        const group = target.group.value;
        const minor = target.minor.checked;

        // create new user
        const profile =  {
            minor: minor,
            firstName: name[0].trim(),
            lastName: name[1].trim()
        };

        // insert user
        Meteor.call('users.insert', email, group, profile);

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
        } else if (event.target.className.includes('make-admin')) {
            // toggle admin state
            Meteor.call('users.addToRole', this._id, 'admin');
        } else if (event.target.className.includes('remove-admin')) {
            // toggle admin state
            Meteor.call('users.removeFromRole', this._id, 'admin');
        }
        else if (event.target.className.includes('edit-user')) {
            // show the modal for the user
            const id = this._id;
            Modal.show('editUser', function () {
                // Under no circumstances, replace `id` below
                // with this._id(). MAJOR BUG.
                // See comment by Soitech:
                // https://github.com/PeppeL-G/bootstrap-3-modal/issues/5
                return Meteor.users.findOne(id);
            });
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
            group: {
                required: true,
                minlength: 5,
                maxlength: 32
            }
        },
        messages: {
            email: {
                required: "Every user needs an email address!"
            }
        }
    });
});
