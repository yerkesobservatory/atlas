import './message.html'

import { Meteor } from 'meteor/meteor';
import { Tracker } from 'meteor/tracker';
import { Accounts } from 'meteor/accounts-base';
import { Programs } from '../api/programs.js';
import { Groups } from '../api/groups.js';
import $ from 'jquery';

//chatbox
import {SimpleChat} from 'meteor/cesarve:simple-chat/config'

Template.message.onCreated(function onCreated() {
    Meteor.subscribe('users');
    Meteor.subscribe('groups');
    console.log(Meteor.user());
});

Template.message.helpers({
    'roomId':function () {
        return Router.current().params.roomId
    },
    'username': function () {
        return Meteor.userId()
    },
    'name': function () {
        return Meteor.user().profile.firstName
    },
    'othername': function () {
        return Router.current().params.othername
    },
    'room': function () {
        return 'conversation'
    },
});


SimpleChat.configure ({
    texts: {
            loadMore: 'Load More',
            placeholder: 'Type message ...',
            button: 'send',
            join: 'joined the',
            left: 'left',
            room: 'room at',

        },
        limit: 50,
        beep: false,
        showViewed: false,
        showReceived: false,
        showJoined: false,
        publishChats: function (roomId, limit) {
            return true;
        },
        allow: function (message, roomId, username, avatar, name) {
            return true;
        },
        onNewMessage: function (msg) {
            var otherId = Router.current().params.otherId;
            var userId = Meteor.userId();
            //Meteor.users.update(userId, {'$addToSet': {'newMessageTo': otherId}});
            Meteor.call('users.newMessageTo', userId, otherId);
            console.log(Meteor.user());
            console.log(msg);
        },
        
        onLeft: function (roomId, username, name,date) {
            //server
            //clear new message
        },
        height: '600px',
        inputTemplate: 'SimpleChatInput',
        loadMoreTemplate: 'LoadMore',
    
})




