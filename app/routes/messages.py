from flask import Blueprint, render_template, request, redirect, url_for, jsonify
from flask_login import login_required, current_user

from app.extensions import db
from app.models import Message, User
from app import controllers

messages_bp = Blueprint('messages', __name__)


@messages_bp.route('/messages')
@login_required
def messages():
    from sqlalchemy import or_
    contacts = (
        db.session.query(User)
        .join(Message, or_(
            (Message.sender_id == User.id) & (Message.receiver_id == current_user.id),
            (Message.receiver_id == User.id) & (Message.sender_id == current_user.id),
        ))
        .filter(User.id != current_user.id)
        .distinct()
        .order_by(User.first_name)
        .all()
    )
    return render_template('messages.html', contacts=contacts, active_user_id=None)


@messages_bp.route('/messages/<int:other_id>')
@login_required
def messages_thread(other_id):
    Message.query.filter_by(
        sender_id=other_id, receiver_id=current_user.id, read=0
    ).update({'read': 1})
    db.session.commit()

    from sqlalchemy import or_
    thread = (
        Message.query
        .filter(or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == other_id),
            (Message.sender_id == other_id) & (Message.receiver_id == current_user.id),
        ))
        .order_by(Message.created_at.asc())
        .all()
    )

    other_user = User.query.get_or_404(other_id)

    contacts = (
        db.session.query(User)
        .join(Message, or_(
            (Message.sender_id == User.id) & (Message.receiver_id == current_user.id),
            (Message.receiver_id == User.id) & (Message.sender_id == current_user.id),
        ))
        .filter(User.id != current_user.id)
        .distinct()
        .order_by(User.first_name)
        .all()
    )

    return render_template('messages.html',
                           contacts=contacts,
                           thread=thread,
                           other_user=other_user,
                           active_user_id=other_id)


@messages_bp.route('/messages/<int:other_id>/send', methods=['POST'])
@login_required
def messages_send(other_id):
    body = (request.json.get('body', '').strip()
            if request.is_json else request.form.get('body', '').strip())
    if not body:
        return jsonify({'error': 'empty'}), 400
    controllers.send_message(current_user.id, other_id, body)
    return jsonify({'ok': True})


@messages_bp.route('/messages/<int:other_id>/poll')
@login_required
def messages_poll(other_id):
    after_id = int(request.args.get('after', 0))
    from sqlalchemy import or_
    rows = (
        Message.query
        .filter(or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == other_id),
            (Message.sender_id == other_id) & (Message.receiver_id == current_user.id),
        ))
        .filter(Message.id > after_id)
        .order_by(Message.created_at.asc())
        .all()
    )
    Message.query.filter(
        Message.sender_id == other_id,
        Message.receiver_id == current_user.id,
        Message.id > after_id
    ).update({'read': 1})
    db.session.commit()
    return jsonify([
        {'id': m.id, 'sender_id': m.sender_id, 'body': m.body,
         'created_at': str(m.created_at)}
        for m in rows
    ])


@messages_bp.route('/api/messages/<int:other_id>/send', methods=['POST'])
@login_required
def api_messages_send(other_id):
    body = (request.json.get('body', '').strip()
            if request.is_json else request.form.get('body', '').strip())
    if not body:
        return jsonify({'error': 'empty'}), 400
    msg = controllers.send_message(current_user.id, other_id, body)
    return jsonify({
        'id':          msg.id,
        'body':        msg.body,
        'created_at':  str(msg.created_at),
        'sender_id':   current_user.id,
        'sender_name': f'{current_user.first_name} {current_user.last_name}',
    })


@messages_bp.route('/api/messages/<int:other_id>/poll')
@login_required
def api_messages_poll(other_id):
    since = request.args.get('since', '1970-01-01 00:00:00')
    from sqlalchemy import or_
    rows = (
        Message.query
        .filter(or_(
            (Message.sender_id == current_user.id) & (Message.receiver_id == other_id),
            (Message.sender_id == other_id) & (Message.receiver_id == current_user.id),
        ))
        .filter(Message.created_at > since)
        .order_by(Message.created_at.asc())
        .all()
    )
    Message.query.filter(
        Message.sender_id == other_id,
        Message.receiver_id == current_user.id,
        Message.created_at > since
    ).update({'read': 1})
    db.session.commit()
    return jsonify([
        {'id': m.id, 'sender_id': m.sender_id, 'body': m.body,
         'created_at': str(m.created_at)}
        for m in rows
    ])
