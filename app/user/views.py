from flask import request

from app.user import user


@user.route('/<user_id>', methods=['PUT'])
def edit(user_id):
    val = request.form.get('title')


pass
