// import routing
import '../imports/router.js';

import { Template } from 'meteor/templating';

import './main.html';

// navbar
import '../imports/ui/navigation.js';

// home
import '../imports/ui/home.js';

// telescope
import '../imports/ui/telescopes.js';

// profile
import '../imports/ui/profile.js';

// observation list
import '../imports/ui/observations.js';

// session list
import '../imports/ui/sessions.js';

// programs
import '../imports/ui/programs.js';

// contact
import '../imports/ui/contact.js';

// auth
import '../imports/auth/login.js';
import '../imports/auth/reset-password.js';


// gui
import '../imports/ui/control.js';

// ==== admin === //
import '../imports/admin/admin.js';
import '../imports/admin/groups.js';

//chatbox
import {SimpleChat} from 'meteor/cesarve:simple-chat/config'

// deny client side updates to users
Meteor.users.deny({
    update() { return true; }
});



SimpleChat.configure ({
    texts:{
        loadMore: 'Load More',
        placeholder: 'Type message ...',
        button: 'send',
        join: 'joined the',
        left: 'left',
        room: 'room at'

    },
    limit: 5,
    beep: true, 
    showViewed: true,
    showReceived: true,
    showJoined: true,
    /*
    publishChats: function(roomId, limi){ //server
       //here the context is the same for a Publications, that mean you have access to this.userId who are asking for subscribe.
       // for example
       //return isLoggedAndHasAccessToSeeMessage(this.userId)
    },
    allow: function(message, roomId, username, avatar, name){
       //here the context is the same for a Methods, thats mean you hace access to this.userId also
       // for example
       //return isLoggedAndHasAccessSendMessages(this.userId)
        return true
    },
    onNewMessage:function(msg){  //both
    },
    onReceiveMessage:function(id, message, room){ //server
        
    },
    onJoin:function(roomId, username, name,date){  //server
    },
    onLeft:function(roomId, username, name,date) { //server
    },
    height: '300px', // Configure the height of the chat
    inputTemplate: 'SimpleChatInput', // In case you want to overwrite the template
    loadMoreTemplate: 'LoadMore', // In case you want to overwrite the template*/
});





