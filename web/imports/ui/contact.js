import './contact.html'

import { Meteor } from 'meteor/meteor';
import { Tracker } from 'meteor/tracker';

import { Programs } from '../api/programs.js';
import { Groups } from '../api/groups.js';
import $ from 'jquery';
import {SimpleChat} from 'meteor/cesarve:simple-chat/config'

Template.contacts_admin.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});

Template.contacts_user.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});


Template.contacts_admin.helpers({
  settings: function() {
    return {
      collection: Meteor.users,
      rowsPerPage: 10,
      showNavigationRowsPerPage: false,
      multiColumnSort: false,
      showNavigation: "never",
      showFilter: false,
      fields: [
        {key:'profile.firstName', label:'First'},
        {key:'profile.lastName', label:'Last'},
        {key:'group', label:'Group'},
        {key:'roles', label:'Role'},
        {key:'', label:'Status'},
        {label: '',
                 tmpl: Template.chatAction
                }]
    }
  },
});

Template.contacts_user.helpers({
  	settings: function() {
    return {
      collection: Meteor.users.find({roles:'admin'}),
      rowsPerPage: 10,
      showNavigationRowsPerPage: false,
      multiColumnSort: false,
      showNavigation: "never",
      showFilter: false,
      fields: [
        {key:'profile.firstName', label:'First'},
        {key:'profile.lastName', label:'Last'},
        {key:'group', label:'Group'},
        {key:'roles', label:'Role'},
        {key:'', label:'Status'},
        {label: '',
                 tmpl: Template.chatAction
                }]
    }
  },
});


Template.chatAction.events({
	'click #message': 
	function () {
			window.location.href = 'message?' + '/id='+Meteor.userId() +'/name=' +Meteor.user().firstName;
		}
	}
);

