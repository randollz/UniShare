import os
import uuid

from flask import (Blueprint, render_template, request, redirect,
                   url_for, flash, jsonify, Response, current_app)
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename

from app.extensions import db
from app.models import Note, SavedNote
from app import controllers

notes_bp = Blueprint('notes', __name__)


@notes_bp.route('/notes')
def notes():
    q    = request.args.get('q', '').strip()
    unit = request.args.get('unit', '').strip().upper()

    query = Note.query
    if q:
        like = f'%{q}%'
        query = query.filter((Note.title.like(like)) | (Note.description.like(like)))
    if unit:
        query = query.filter(Note.unit_code == unit)
    notes_list = query.order_by(Note.upvotes.desc(), Note.created_at.desc()).all()

    return render_template('notes.html', notes=notes_list, q=q, unit=unit)


@notes_bp.route('/create_note', methods=['GET', 'POST'])
@login_required
def create_note():
    if request.method == 'POST':
        try:
            note = controllers.create_note(current_user.id, request.form)
            attachment = request.files.get('attachment')
            if attachment and attachment.filename:
                allowed_mimes = {'application/pdf', 'application/msword',
                                 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                                 'image/jpeg', 'image/png'}
                mime = attachment.mimetype
                if mime not in allowed_mimes:
                    flash('Unsupported file type. Please upload PDF, DOCX, JPG or PNG.', 'error')
                    return render_template('create_note.html', errors={}, form=request.form)
                attachment.seek(0, 2)
                if attachment.tell() > 10 * 1024 * 1024:
                    flash('File is too large (max 10 MB).', 'error')
                    return render_template('create_note.html', errors={}, form=request.form)
                attachment.seek(0)
                upload_dir = os.path.join(current_app.static_folder, 'uploads', 'notes')
                os.makedirs(upload_dir, exist_ok=True)
                fname = f"{uuid.uuid4().hex}_{secure_filename(attachment.filename)}"
                attachment.save(os.path.join(upload_dir, fname))
                note.file_path = f"uploads/notes/{fname}"
                note.file_name = attachment.filename
                db.session.commit()
            flash('Notes shared!', 'success')
            return redirect(url_for('notes.notes'))
        except ValueError as e:
            flash(str(e), 'error')
    return render_template('create_note.html', errors={}, form=request.form)


@notes_bp.route('/upvote_note/<int:note_id>', methods=['POST'])
@login_required
def upvote_note(note_id):
    note = Note.query.get_or_404(note_id)
    note.upvotes += 1
    db.session.commit()
    return redirect(url_for('notes.notes'))


@notes_bp.route('/notes/<int:note_id>')
def view_note(note_id):
    note = Note.query.get_or_404(note_id)
    is_saved = False
    if current_user and current_user.is_authenticated:
        is_saved = SavedNote.query.filter_by(
            user_id=current_user.id, note_id=note_id).first() is not None
    return render_template('note_detail.html', note=note, is_saved=is_saved)


@notes_bp.route('/notes/<int:note_id>/download')
def download_note(note_id):
    from flask import send_from_directory
    note = Note.query.get_or_404(note_id)
    if note.file_path:
        directory = os.path.join(current_app.static_folder, 'uploads', 'notes')
        filename = os.path.basename(note.file_path)
        return send_from_directory(directory, filename,
                                   as_attachment=True,
                                   download_name=note.file_name or filename)
    content = (
        f"{note.title}\n\n"
        f"Unit: {note.unit_code}\n"
        f"Semester: {note.semester}\n\n"
        f"{note.description}"
    )
    return Response(content, mimetype='text/plain',
                    headers={'Content-Disposition': f'attachment; filename=note-{note_id}.txt'})


@notes_bp.route('/library')
@login_required
def library():
    saved = (SavedNote.query
             .filter_by(user_id=current_user.id)
             .order_by(SavedNote.saved_at.desc())
             .all())
    saved_notes = [sn.note for sn in saved]
    saved_ids   = {sn.note_id for sn in saved}
    my_notes    = Note.query.filter_by(author_id=current_user.id).order_by(Note.created_at.desc()).all()
    return render_template('library.html', saved_notes=saved_notes,
                           my_notes=my_notes, saved_ids=saved_ids)


@notes_bp.route('/save_note/<int:note_id>', methods=['POST'])
@login_required
def save_note(note_id):
    note = Note.query.get_or_404(note_id)
    existing = SavedNote.query.filter_by(user_id=current_user.id, note_id=note_id).first()
    if existing:
        db.session.delete(existing)
        db.session.commit()
        return jsonify({'saved': False})
    sn = SavedNote(user_id=current_user.id, note_id=note_id)
    db.session.add(sn)
    db.session.commit()
    return jsonify({'saved': True})
