"""
Tests for medusa.py.

Run with:
    pytest -v

Run with coverage:
    pytest --cov=medusa --cov-branch --cov-report=term-missing
"""
## Allow testing without installing the app.
import os
import sys
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)


from unittest.mock import patch

import pytest

import medusa


@pytest.fixture
def client(tmp_path):
    """Create a Flask test client using an isolated temporary directory."""
    medusa.BASE_DIR = str(tmp_path)

    medusa.app.config.update(
        TESTING=True,
        WTF_CSRF_ENABLED=False,
    )

    with medusa.app.test_client() as client:
        yield client


@pytest.fixture
def script(tmp_path):
    """Create a sample Python script in the temporary modules directory."""
    path = tmp_path / "example.py"
    path.write_text("print('hello world')\n")
    return path


## ---------------------------------------------------------------------------
## target_aquisition()
## ---------------------------------------------------------------------------

class TestTargetAcquisition:

    def test_edit_has_priority(self):
        form = {
            "edit": "example.py",
            "delete": "example.py",
            "add": "1",
            "menu": "1",
            "modify": "1",
            "submit": "example.py",
        }

        assert medusa.target_aquisition(form) == "edit"

    def test_delete(self):
        assert medusa.target_aquisition(
            {"delete": "example.py"}
        ) == "delete"

    def test_add(self):
        assert medusa.target_aquisition({"add": "1"}) == "add"

    def test_menu(self):
        assert medusa.target_aquisition({"menu": "1"}) == "menu"

    def test_modify(self):
        assert medusa.target_aquisition({"modify": "1"}) == "modify"

    def test_submit(self):
        assert medusa.target_aquisition(
            {"submit": "example.py"}
        ) == "example.py"

    def test_missing_submit_returns_back(self):
        assert medusa.target_aquisition({}) == "back"


## ---------------------------------------------------------------------------
## target_handler()
## ---------------------------------------------------------------------------

class TestTargetHandler:

    def test_back(self, client):
        with client.application.test_request_context():
            response = medusa.target_handler("back", {})

        assert response.status_code == 302
        assert response.location.endswith("/")

    @pytest.mark.parametrize("target", ["edit", "delete"])
    def test_edit_and_delete(self, client, target):
        form = {target: "example.py"}

        with client.application.test_request_context():
            response = medusa.target_handler(target, form)

        assert response.status_code == 302
        assert response.location.endswith(
            f"/{target}/example.py"
        )

    @pytest.mark.parametrize(
        "target",
        ["add", "modify", "menu"],
    )
    def test_static_targets(self, client, target):
        with client.application.test_request_context():
            response = medusa.target_handler(target, {})

        assert response.status_code == 302

    def test_directory_redirects_back(self, client, tmp_path):
        directory = tmp_path / "directory"
        directory.mkdir()

        with client.application.test_request_context():
            response = medusa.target_handler(str(directory), {})

        assert response.status_code == 302
        assert response.location.endswith("/")

    def test_existing_file_redirects_to_execute(
        self,
        client,
        script,
    ):
        with client.application.test_request_context():
            response = medusa.target_handler(
                script.name,
                {},
            )

        assert response.status_code == 302
        assert "/execute/example.py" in response.location

    def test_unknown_target_returns_none(self, client):
        with client.application.test_request_context():
            response = medusa.target_handler(
                "does-not-exist.py",
                {},
            )

        assert response is None


## ---------------------------------------------------------------------------
## HTML helper functions
## ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("contents", "expected"),
    [
        (
            "hello",
            '<textarea class="output-textarea" disabled>'
            "hello"
            "</textarea>",
        ),
        (
            "",
            '<textarea class="output-textarea" disabled>'
            "</textarea>",
        ),
        (
            "line 1\nline 2",
            '<textarea class="output-textarea" disabled>'
            "line 1\nline 2"
            "</textarea>",
        ),
    ],
)
def test_output_textarea(contents, expected):
    assert medusa.output_textarea(contents) == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            None,
            '<p class="success-msg">Success</p>',
        ),
        (
            "Saved",
            '<p class="success-msg">Saved</p>',
        ),
        (
            "Custom message",
            '<p class="success-msg">Custom message</p>',
        ),
    ],
)
def test_success_msg(message, expected):
    if message is None:
        assert medusa.success_msg() == expected
    else:
        assert medusa.success_msg(message) == expected


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        (
            None,
            '<p class="fail-msg">Failed</p>',
        ),
        (
            "Custom failure",
            '<p class="fail-msg">Custom failure</p>',
        ),
    ],
)
def test_fail_msg(message, expected):
    if message is None:
        assert medusa.fail_msg() == expected
    else:
        assert medusa.fail_msg(message) == expected


## ---------------------------------------------------------------------------
## Main route
## ---------------------------------------------------------------------------

def test_medusa_get(client):
    with patch(
        "medusa.dir_contents",
        return_value=["example.py", "test.py"],
    ) as mock_dir_contents:
        response = client.get("/")

    assert response.status_code == 200

    mock_dir_contents.assert_called_once_with(
        medusa.BASE_DIR,
        filenames_only=True,
    )


def test_medusa_alias_route(client):
    response = client.get("/medusa")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("form_data", "expected"),
    [
        ({"edit": "example.py"}, "/edit/example.py"),
        ({"delete": "example.py"}, "/delete/example.py"),
        ({"add": "1"}, "/add"),
        ({"menu": "1"}, "/menu"),
        ({"modify": "1"}, "/edit"),
        ({}, "/"),
    ],
)
def test_medusa_post(client, form_data, expected):
    response = client.post("/", data=form_data)

    assert response.status_code == 302
    assert response.location.endswith(expected)


def test_medusa_post_submit_existing_file(client, script):
    response = client.post(
        "/",
        data={"submit": script.name},
    )

    assert response.status_code == 302
    assert "/execute/example.py" in response.location


## ---------------------------------------------------------------------------
## /execute/<script>
## ---------------------------------------------------------------------------

def test_execute_success(client):
    result = {
        "code": 0,
        "output": "hello world",
    }

    with patch(
        "medusa.pysub",
        return_value=result,
    ) as mock_pysub:
        response = client.get("/execute/example.py")

    assert response.status_code == 302
    assert response.location.endswith("/")

    mock_pysub.assert_called_once_with(
        script=f"{medusa.BASE_DIR}/example.py"
    )


def test_execute_failure(client):
    result = {
        "code": 1,
        "output": "something went wrong",
    }

    with patch(
        "medusa.pysub",
        return_value=result,
    ) as mock_pysub:
        response = client.get("/execute/example.py")

    assert response.status_code == 302
    assert response.location.endswith("/")

    mock_pysub.assert_called_once_with(
        script=f"{medusa.BASE_DIR}/example.py"
    )


def test_execute_success_flashes_output(client):
    result = {
        "code": 0,
        "output": "successful output",
    }

    with patch("medusa.pysub", return_value=result):
        response = client.get(
            "/execute/example.py",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"successful output" in response.data
    assert b"success-msg" in response.data


def test_execute_failure_flashes_output(client):
    result = {
        "code": 42,
        "output": "failure output",
    }

    with patch("medusa.pysub", return_value=result):
        response = client.get(
            "/execute/example.py",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"failure output" in response.data
    assert b"fail-msg" in response.data


## ---------------------------------------------------------------------------
## /add
## ---------------------------------------------------------------------------

def test_add_get(client):
    response = client.get("/add")

    assert response.status_code == 302
    assert response.location.endswith("/edit/new_script.py")


def test_add_post(client):
    response = client.post("/add")

    assert response.status_code == 302
    assert response.location.endswith("/edit/new_script.py")


## ---------------------------------------------------------------------------
## /edit/<script>
## ---------------------------------------------------------------------------

def test_edit_get_missing_file(client):
    with patch(
        "medusa.file_exists",
        return_value=False,
    ) as mock_exists:
        response = client.get("/edit/example.py")

    assert response.status_code == 200

    mock_exists.assert_called_once_with(
        f"{medusa.BASE_DIR}/example.py"
    )


def test_edit_get_existing_file(client):
    with patch(
        "medusa.file_exists",
        return_value=True,
    ), patch(
        "medusa.file_read",
        return_value="print('hello')",
    ) as mock_read:
        response = client.get("/edit/example.py")

    assert response.status_code == 200
    assert b"example.py" in response.data

    mock_read.assert_called_once_with(
        f"{medusa.BASE_DIR}/example.py"
    )


def test_edit_post_back(client):
    response = client.post(
        "/edit/example.py",
        data={
            "submit": "back",
            "script_name": "example.py",
            "contents": "print('hello')",
        },
    )

    assert response.status_code == 302
    assert response.location.endswith("/")


def test_edit_post_save_success(client):
    with patch(
        "medusa.file_safe_write",
        return_value=True,
    ) as mock_write:
        response = client.post(
            "/edit/example.py",
            data={
                "submit": "save",
                "script_name": "example.py",
                "contents": "print('hello')",
            },
            follow_redirects=True,
        )

    assert response.status_code == 200

    mock_write.assert_called_once_with(
        f"{medusa.BASE_DIR}/example.py",
        "print('hello')",
    )

    assert b"Saved" in response.data
    assert b"success-msg" in response.data


def test_edit_post_save_failure(client):
    with patch(
        "medusa.file_safe_write",
        return_value=False,
    ) as mock_write:
        response = client.post(
            "/edit/example.py",
            data={
                "submit": "save",
                "script_name": "example.py",
                "contents": "print('hello')",
            },
            follow_redirects=True,
        )

    assert response.status_code == 200

    mock_write.assert_called_once_with(
        f"{medusa.BASE_DIR}/example.py",
        "print('hello')",
    )

    assert b"fail-msg" in response.data


## ---------------------------------------------------------------------------
## /edit
## ---------------------------------------------------------------------------

def test_modify_get(client):
    with patch(
        "medusa.dir_contents",
        return_value=["one.py", "two.py"],
    ) as mock_contents:
        response = client.get("/edit")

    assert response.status_code == 200

    mock_contents.assert_called_once_with(
        medusa.BASE_DIR,
        filenames_only=True,
    )


@pytest.mark.parametrize(
    ("form_data", "expected"),
    [
        ({"edit": "one.py"}, "/edit/one.py"),
        ({"delete": "one.py"}, "/delete/one.py"),
        ({"add": "1"}, "/add"),
        ({"menu": "1"}, "/menu"),
        ({"modify": "1"}, "/edit"),
        ({}, "/"),
    ],
)
def test_modify_post(client, form_data, expected):
    response = client.post(
        "/edit",
        data=form_data,
    )

    assert response.status_code == 302
    assert response.location.endswith(expected)


## ---------------------------------------------------------------------------
## /delete/<script>
## ---------------------------------------------------------------------------

def test_delete_get(client):
    response = client.get("/delete/example.py")

    assert response.status_code == 200
    assert b"example.py" in response.data


def test_delete_post_back(client):
    response = client.post(
        "/delete/example.py",
        data={"submit": "back"},
    )

    assert response.status_code == 302
    assert response.location.endswith("/")


def test_delete_post_success(client):
    with patch(
        "medusa.file_delete",
        return_value=True,
    ) as mock_delete:
        response = client.post(
            "/delete/example.py",
            data={"delete": "example.py"},
            follow_redirects=True,
        )

    assert response.status_code == 200

    mock_delete.assert_called_once_with(
        f"{medusa.BASE_DIR}/example.py"
    )

    assert b"Deleted" in response.data
    assert b"success-msg" in response.data


def test_delete_post_failure(client):
    with patch(
        "medusa.file_delete",
        return_value=False,
    ) as mock_delete:
        response = client.post(
            "/delete/example.py",
            data={"delete": "example.py"},
            follow_redirects=True,
        )

    assert response.status_code == 200

    mock_delete.assert_called_once_with(
        f"{medusa.BASE_DIR}/example.py"
    )

    assert b"fail-msg" in response.data


def test_delete_post_unrelated_target(client):
    response = client.post(
        "/delete/example.py",
        data={"add": "1"},
    )

    assert response.status_code == 200
    assert b"example.py" in response.data


## ---------------------------------------------------------------------------
## /menu
## ---------------------------------------------------------------------------

def test_menu_get(client):
    response = client.get("/menu")

    assert response.status_code == 200


@pytest.mark.parametrize(
    ("form_data", "expected"),
    [
        ({"edit": "example.py"}, "/edit/example.py"),
        ({"delete": "example.py"}, "/delete/example.py"),
        ({"add": "1"}, "/add"),
        ({"modify": "1"}, "/edit"),
        ({}, "/"),
    ],
)
def test_menu_post(client, form_data, expected):
    response = client.post(
        "/menu",
        data=form_data,
    )

    assert response.status_code == 302
    assert response.location.endswith(expected)


## ---------------------------------------------------------------------------
## Application sanity checks
## ---------------------------------------------------------------------------

def test_application_has_expected_routes():
    routes = {
        rule.rule
        for rule in medusa.app.url_map.iter_rules()
    }

    assert "/" in routes
    assert "/medusa" in routes
    assert "/add" in routes
    assert "/edit" in routes
    assert "/edit/<script>" in routes
    assert "/delete/<script>" in routes
    assert "/execute/<script>" in routes
    assert "/menu" in routes


def test_base_dir_is_defined():
    assert isinstance(medusa.BASE_DIR, str)
    assert medusa.BASE_DIR


def test_medusa_form_can_be_instantiated(client):
    with client.application.test_request_context():
        form = medusa.MedusaForm()

    assert form is not None


## ---------------------------------------------------------------------------
## Test invalid forms
## ---------------------------------------------------------------------------


def test_medusa_post_invalid_or_incomplete_data(client):
    response = client.post(
        "/",
        data={"edit": ""},
    )

    assert response.status_code == 302


def test_edit_post_invalid_or_incomplete_data(client):
    response = client.post(
        "/edit/example.py",
        data={
            "submit": "save",
            "script_name": "",
            "contents": "",
        },
    )

    assert response.status_code == 302


def test_modify_post_invalid_or_incomplete_data(client):
    response = client.post(
        "/edit",
        data={"edit": ""},
    )

    assert response.status_code == 302


def test_delete_post_invalid_or_incomplete_data(client):
    response = client.post(
        "/delete/example.py",
        data={"delete": ""},
    )

    assert response.status_code == 302


def test_menu_post_invalid_or_incomplete_data(client):
    response = client.post(
        "/menu",
        data={"edit": ""},
    )

    assert response.status_code == 302