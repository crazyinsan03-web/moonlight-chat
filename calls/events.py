from flask import request
from flask_socketio import emit

def register_call_events(socketio):
    
    @socketio.on('call-user')
    def handle_call_user(data):
        target_user_id = data.get('to')
        offer = data.get('offer')
        caller_id = data.get('from')
        call_type = data.get('type')
        print(f"Call from {caller_id} to {target_user_id}")
        
        emit('incoming-call', {
            'from': caller_id,
            'offer': offer,
            'type': call_type
        }, room=target_user_id)

    @socketio.on('answer-call')
    def handle_answer_call(data):
        target_user_id = data.get('to')
        answer = data.get('answer')
        emit('call-accepted', {
            'answer': answer,
            'from': data.get('from')
        }, room=target_user_id)

    @socketio.on('ice-candidate')
    def handle_ice_candidate(data):
        target_user_id = data.get('to')
        candidate = data.get('candidate')
        emit('ice-candidate', {
            'candidate': candidate,
            'from': data.get('from')
        }, room=target_user_id)

    # --- YE DO EVENTS ADD KARDE (ZAROORI HAI) ---

    @socketio.on('end-call')
    def handle_end_call(data):
        target_user_id = data.get('to')
        # Dusre bande ko batao ki call cut gayi hai
        emit('call-ended', room=target_user_id)

    @socketio.on('reject-call')
    def handle_reject_call(data):
        target_user_id = data.get('to')
        # Caller ko notify karo ki call reject ho gayi
        emit('call-ended', room=target_user_id)