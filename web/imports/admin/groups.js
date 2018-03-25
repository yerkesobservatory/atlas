import './groups.html';

import { Groups } from '../api/groups.js';
import $ from 'jquery';

// subscribe to users
Template.adminGroups.onCreated(function onCreated() {
    Meteor.subscribe('groups');
});

Template.adminGroups.helpers({
    settings() {
        return {
            collection: Groups,
            showRowCount: true,
            showNavigationRowsPerPage: true,
            showFilter: false,
            noDataTmpl: Template.noGroups,
            fields: [
                {key: 'name',
                 label: 'Name'},
                {key: 'priority',
                 label: 'Priority'},
                {key: 'defaultPriority',
                 label: 'Default Priority'},
                {key: 'defaultMaxQueueTime',
                 label: 'Default Queue Usage (s)'},
                {label: '',
                 tmpl: Template.groupAction
                 }
            ]
        };
    }
});

// event handlers
Template.adminGroups.events({
    // submitting new programs
    'submit .new-group'(event) {

        // clear any past alerts
        CoffeeAlerts.clearSeen();

        // prevent default browser
        event.preventDefault();

        // clear 'success' formatting from form
        $('.new-group').find('.form-group').removeClass('has-success');

        // get value from form
        const target = event.target;
        const name = target.name.value;
        const priority = Number(target.priority.value);
        const defPriority = Number(target.defpriority.value);
        const defMaxQueueTime = Number(target.defmaxtime.value);

        // check that values are sensible
        if ((defPriority < 1) || (defPriority > 5)) {
            CoffeeAlerts.error('The default user priority must be greater than 1 and less than 5.');
            return;
        }
        if (defMaxQueueTime < 0) {
            CoffeeAlerts.error('The default queue usage must be greater than 0 s.');
            return;
        }
        if (priority < 0) {
            CoffeeAlerts.error('The group priority must be greater than 1 and less than 5.');
            return;
        }

        // submit new program
        Meteor.call('groups.insert', name, priority, defPriority, defMaxQueueTime);

        // reset form
        $('.new-group')[0].reset();

    },

    // on press of the delete button
    'click .reactive-table tbody tr': function (event) {
        event.preventDefault();
        const id = this._id;
        // checks if the actual clicked element has the class `delete`
        if (event.target.className.includes('delete')) {
            // delete observation
            Meteor.call('groups.remove', this._id);
        }
        else if (event.target.className.includes('edit-group')) {
            Modal.show('editGroup', function () {
                return Groups.findOne(id);
            });
        }
    }
});
