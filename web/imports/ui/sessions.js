import './sessions.html';

import { Sessions } from '../api/sessions.js';
import { Programs } from '../api/programs.js';

// subscribe to sessions stream
Template.sessions.onCreated(function onCreated() {
    Meteor.subscribe('sessions');
    Meteor.subscribe('programs');
});

// access sessions
Template.sessions.helpers({
    sessions() {
	return Sessions.find({}, { sort: {'createDate': -1 } });
    },
    programs() {
	return Programs.find({owner: Meteor.userId()}, { sort: {'createDate': -1 } });
    },
     settings() {
	return {
	    collection: Sessions,
	    showRowCount: true,
	    showNavigationRowsPerPage: false,
	    noDataTmpl: Template.noSessions,
	    fields: [
		{key: 'start',
		 label: 'Start'},
		{key: 'end',
		 label: 'End'},
		{key: 'programId',
		 label: 'Program',
		 fn: function (value, object, key) {
		     const program = Programs.findOne(value);
		     if (program) {
			 return program.name;
		     }
		 }
		},
		{key: 'email',
		 label: 'User'},
		{label: '',
		 fn: function(value, object, key) {
		     if (object.owner == Meteor.userId()) {
		     	 return new Spacebars.SafeString('<a href="#" class="btn btn-danger delete">Delete</a>');
		     }
		 }
		 },
		]
	};
    }
});

// event handlers
Template.sessions.events({
    'submit .new-session'(event) {

	// prevent default browser
	event.preventDefault();

	// get value from form
	const target = event.target;
	const programId = target.program.value;
	const startDate = target.startDate.value+' '+target.startTime.value;
	const endDate = target.endDate.value+' '+target.endTime.value;

	// submit new observation
	Meteor.call('sessions.insert', programId, startDate, endDate);

    },
    // on press of the delete button
    'click .reactive-table tbody tr': function (event) {
	event.preventDefault();
	// checks if the actual clicked element has the class `delete`
	if (event.target.className.includes('delete')) {
	    // delete observation
	    Meteor.call('sessions.remove', this._id);
	}
    }
});

