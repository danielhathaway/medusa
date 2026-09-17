## Usage: flask --app "medusa" run
## See: https://flask.palletsprojects.com/en/stable/
## See: https://jinja.palletsprojects.com/en/stable/templates/

import os
import secrets
from flask import Flask, request, redirect, render_template, url_for, flash
from flask_wtf import FlaskForm, CSRFProtect
from chempy.pysub import pysub
from chempy.files import (
    file_read,
    file_safe_write,
    file_delete,
    file_exists,
    parent_path,
    dir_contents)
from chempy.conf import read_conf


app = Flask(__name__)
csrf = CSRFProtect(app)
## Generate a new secret key for use until the app is no longer served.
app.secret_key = secrets.token_hex()
app.add_url_rule('/', endpoint='medusa')
app.add_url_rule('/medusa', endpoint='medusa')
app.add_url_rule('/', endpoint='back')
csrf = CSRFProtect(app)


## Check for config file values
config = read_conf('medusa.conf')
if 'base_dir' in config:
    BASE_DIR = config['base_dir']
else:
    BASE_DIR = f'{parent_path(os.path.realpath(__file__))}{os.sep}modules'


class MedusaForm(FlaskForm):
    ## This class just needs to be instantiated to use it's CSRF token functionalty.
    ## Python requires at least one indented line after the class declaration:
    unused_variable = 0


def target_aquisition(request_form):
    if 'edit' in request_form:
        target = 'edit'
    elif 'delete' in request_form:
        target = 'delete'
    elif 'add' in request_form:
        target = 'add'
    elif 'menu' in request_form:
        target = 'menu'
    elif 'modify' in request_form:
        target = 'modify'
    else:
        try:
            target = request_form['submit']
        except:
            target = 'back'
    return target


def target_handler(target, request_form):
    if target == 'back':
        return redirect(url_for('back'))
    elif target == 'edit' or target == 'delete':
        return redirect(url_for(target, script=request_form[target]))
    elif (target == 'add' or (target == 'modify' or target == 'menu')):
        return redirect(url_for(target))
    elif os.path.isdir(target):
        return redirect(url_for('back'))
    elif os.path.isfile(f'{BASE_DIR}{os.sep}{target}'):
        return redirect(url_for('execute', script=target))


def output_textarea(contents:str):
    return f'<textarea class="output-textarea" disabled>{contents}</textarea>'


def success_msg(message:str = 'Success'):
    return f'<p class="success-msg">{message}</p>'


def fail_msg(message:str = 'Failed'):
    return f'<p class="fail-msg">{message}</p>'


@app.route('/', methods=['GET', 'POST'])
def medusa():
    form = MedusaForm()
    files = dir_contents(BASE_DIR, filenames_only=True)
    if request.method == 'POST' and form.validate_on_submit():
        target = target_aquisition(request.form)
        return target_handler(target, request.form)
    return render_template('medusa/index.html', files=files)


@app.route('/execute/<script>', methods=['GET', 'POST'])
def execute(script):
    result = pysub(script=f'{BASE_DIR}{os.sep}{script}')
    if result['code'] == 0:
        flash(f'{success_msg()}{output_textarea(result['output'])}')
    else:
        flash(f'{fail_msg()}{output_textarea(result['output'])}')
    return redirect(url_for('back'))


@app.route('/add', methods=['GET', 'POST'])
def add():
    return redirect(url_for('edit', script='new_script.py'))


@app.route('/edit/<script>', methods=['GET', 'POST'])
def edit(script):
    form = MedusaForm()
    if file_exists(f'{BASE_DIR}{os.sep}{script}'):
        file_contents = file_read(f'{BASE_DIR}{os.sep}{script}')
    else:
        file_contents = ''
    if request.method == 'POST' and form.validate_on_submit():
        target = target_aquisition(request.form)
        if target == 'back':
            return redirect(url_for('back'))
        else:
            if file_safe_write(f'{BASE_DIR}{os.sep}{request.form['script_name']}', request.form['contents']):
                flash(success_msg('Saved'))
            else:
                flash(fail_msg())
            return redirect(url_for('back'))
    else:
        return render_template('medusa/edit.html', script=script, file_contents=file_contents)


@app.route('/edit', methods=['GET', 'POST'])
def modify():
    form = MedusaForm()
    files = dir_contents(BASE_DIR, filenames_only=True)
    if request.method == 'POST' and form.validate_on_submit():
        target = target_aquisition(request.form)
        return target_handler(target, request.form)
    return render_template('medusa/modify.html', files=files)


@app.route('/delete/<script>', methods=['GET', 'POST'])
def delete(script):
    form = MedusaForm()
    if request.method == 'POST' and form.validate_on_submit():
        target = target_aquisition(request.form)
        if target == 'back':
            return redirect(url_for('back'))
        elif target == 'delete':
            if file_delete(f'{BASE_DIR}{os.sep}{script}'):
                flash(success_msg('Deleted'))
            else:
                flash(fail_msg())
            return redirect(url_for('back'))
    else:
        return render_template('medusa/delete.html', script=script)


@app.route('/menu', methods=['GET', 'POST'])
def menu():
    form = MedusaForm()
    if request.method == 'POST' and form.validate_on_submit():
        target = target_aquisition(request.form)
        return target_handler(target, request.form)
    return render_template('medusa/menu.html')
