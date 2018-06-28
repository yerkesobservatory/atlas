import './contact.html'

import { Meteor } from 'meteor/meteor';
import { Tracker } from 'meteor/tracker';

import { Programs } from '../api/programs.js';
import { Groups } from '../api/groups.js';
import $ from 'jquery';
import {SimpleChat} from 'meteor/cesarve:simple-chat/config'

Template.contacts_admins.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});

Template.contacts_users.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});

Template.chatAction.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
});

Template.contacts_users.helpers({
  settings: function() {
    return {
      collection: Meteor.users.find({roles:'user'}),
        showRowCount: true,
        showNavigationRowsPerPage: false,
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

Template.contacts_admins.helpers({
  	settings: function() {
    return {
      	collection: Meteor.users.find({roles:'admin'}),
        showRowCount: true,
        showNavigationRowsPerPage: false,
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


Template.contact.events({
	/*'click #message': 
	function () {
			window.location.href = 'message' + '/'+'roomID' +'/'+Meteor.user().firstName;
		}*/
	'click .reactive-table tbody tr': 
	function (event) {
        event.preventDefault();
        // checks if the actual clicked element has the class `delete`
        if (event.target.id = ('message')) {
        	var roomid = '';
        	if ( this._id <= Meteor.userId()){
        		roomid = this._id + Meteor.userId();
        	} else {
        		roomid = Meteor.userId() + this._id;
        	}
            window.location.href = 'message' + '/'+roomid+'/'+Meteor.userId()+'/'+this.profile.firstName+this.profile.lastName ;
        }
    },
});

