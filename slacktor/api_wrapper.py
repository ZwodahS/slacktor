"""
Author: Eric Ng

Github: https://github.com/ZwodahS

Api wrappers is a tornado wrapper that allows developers to describe rest api
in the form of a dictionary and call them like a method.

This is written with support for python2's tornado, which means tornado.gen.Return
instead of just return.

As of now, this is not feature complete, please extend as you see fit.

Some note:

You should set retries_status for POST/PUT/DELETE call to empty
"""

"""
Some TODO
1. allow params to the dot separated. (mainly for json body)
"""
import re
import six
import json
import time
import logging

import tornado.gen
import tornado.httpclient

#################### Exceptions #####################
class RestAPIParserException(Exception):
    pass


class RestAPIRuntimeException(Exception):
    pass

#################### Utility functions #####################


@tornado.gen.coroutine
def _fetch_with_retries(http_client, request, max_tries=None, retries_status=None,
        retry_delay=5):
    """Fetch a request with retries

    http_client         The httpclient to use
    request             The request to fetch
    max_tries           The max number of tries to try (default: 3)
    retries_status      The status to retry on. (default (599, 503, 504))
                        (provide a list/tuple of int)
    """
    max_tries = max_tries if max_tries is not None else 5
    retries_status = retries_status if retries_status is not None else tuple()

    tries = 0
    response = None
    while tries < max_tries:
        tries += 1
        response = yield http_client.fetch(request, raise_error=False)
        if response is None or response.code in retries_status:
            logging.debug("Fail to fetch: {url}, Code: {code}, retrying ... {current_try}/{max_try}".format(
                url=request.url, code=response.code, current_try=tries, max_try=max_tries))
            yield tornado.gen.Task(tornado.ioloop.IOLoop.instance().add_timeout,
                time.time() + retry_delay)
            continue
        raise tornado.gen.Return(response)
    raise tornado.gen.Return(response)

fetch_with_retries = _fetch_with_retries

#################### Main object #################
class RestAPI(object):
    """
    Usage:
    from api_wrapper import RestAPI

    user_api_config = {
        "protocol": RestAPI.HTTP,
        "url": "/v1/users",
        "params": { "id" : { "type": "string" } },
        "method": RestAPI.GET,
        "host": "some.random.ip.here",
        "headers": {},
    }

    get_user_by_id = RestAPI.from_config(user_api_config)

    response = yield get_user_by_id(id="randomid")

    do not use the constructor of RestAPI directly
    """

    ##### Commonly used constants #######
    HTTP="http"
    HTTPS="https"

    GET="GET"
    POST="POST"
    PUT="PUT"
    DELETE="DELETE"

    FORM="form"
    PLAINTEXT="plaintext"
    JSON="json"

    URL_PARAMS_REGEX = re.compile("(\{.*?\})")
    REQUEST_CONTENT_TYPE = (JSON, FORM)

    TYPE_STRING = "string"
    TYPE_INT = "int"
    TYPE_FLOAT = "float"
    TYPE_DICT = "dict"
    TYPE_COMMA_STRING = "comma_string"
    TYPE_BOOL = "bool"
    TYPE_LIST = "list"
    TYPE_BOOL_STRING = "bool_string"
    PARAM_TYPES = (
        TYPE_STRING, TYPE_INT, TYPE_FLOAT,
        TYPE_DICT, TYPE_COMMA_STRING,
        TYPE_BOOL, TYPE_BOOL_STRING
    )

    def __init__(self):
        self.http_client = tornado.httpclient.AsyncHTTPClient()
        self.host = None
        self.auth_username = None
        self.auth_password = None
        self.post_response_hooks = []
        self.headers = {}
        self.retries_status = {502, 503, 504, 599}
        self.max_tries = 3
        self._default_values = {}
        self._partial_values = {}
        self.cache = {}
        self.decode = None

    @classmethod
    def from_config(cls, config):
        api = RestAPI()
        api.protocol = config.get("protocol") if "protocol" in config else RestAPI.HTTP
        api.host = config.get("host") if "host" in config else None
        api.url = config.get("url")
        api.method = config.get("method") if "method" in config else RestAPI.GET
        if api.method in (RestAPI.PUT, RestAPI.POST):
            api.request_body_type = (config.get("request_body_type") if
                    "request_body_type" in config else RestAPI.FORM)
        else:
            api.request_body_type = None
        api.url_params = RestAPI.URL_PARAMS_REGEX.findall(api.url)
        api.url_params = [ a[1:-1] for a in api.url_params ]

        if "headers" in config:
            api.headers.update(config["headers"])
        api.params = config.get("params") if "params" in config else {}
        # set up basic structure
        for key, param in six.iteritems(api.params):
            if "default" in param:
                api._default_values[key] = param["default"]
        return api

    def set(self, **params):
        """Set the other stuffs in one shot

        The stuffs that can be set here are
        decode, retries_status, max_tries

        decode                  what encoding to decode the response to. (default None)
        retries_status          what status to retry the request on. (default 502, 503, 504, 599)
        max_tries               the number of tries when trying to perform the request. (default 3)
        """
        if "decode" in params:
            self.decode = params["decode"]
        if "retries_status" in params:
            self.retries_status = params["retries_status"]
        if "max_tries" in params:
            self.max_tries = params["max_tries"]
        return self

    def copy(self):
        """Make a copy of this api
        """
        api = RestAPI()
        api.protocol = self.protocol
        api.url = self.url
        api.method = self.method
        api.request_body_type = self.request_body_type
        api.url_params = self.url_params
        api.params = self.params

        # mutable values
        api._default_values.update(self._default_values)
        api._partial_values.update(self._partial_values)

        api.http_client = self.http_client
        api.host = self.host
        api.auth_username = self.auth_username
        api.auth_password = self.auth_password
        api.headers.update(self.headers)
        api.post_response_hooks = [ h for h in self.post_response_hooks ]
        return api

    def auth(self, auth_username, auth_password, create_new=False):
        """Add auth header to this api

        auth_username           The username part of the auth
        auth_password           The password part of the auth
        create_new              if True a new RestAPI object is returned,
                                else the current one is modified (default: False)

        return                  instance of RestAPI
        """
        copy = self.copy() if create_new else self
        copy.auth_username = auth_username
        copy.auth_password = auth_password
        return copy

    def add_headers(self, headers, create_new=False):
        """Add default headers to the api

        headers                 key/value pair for headers
        create_new              if True a new RestAPI object is returned,
                                else the current one is modified (default: False)

        return                  instance of RestAPI
        """
        copy = self.copy() if create_new else self
        copy.headers.update(headers)
        return copy

    def set_host(self, host, create_new=False):
        """Set the host for this endpoint
        """
        copy = self.copy() if create_new else self
        copy.host = host
        return copy

    def set_httpclient(self, http_client, create_new=False):
        """Set a default AsyncHTTPClient to use

        http_client             a tornado.httpclient.AsyncHTTPClient instance
        create_new              if True a new RestAPI object is returned,
                                else the current one is modified (default: False)

        return                  instance of RestAPI
        """
        copy = self.copy() if create_new else self
        copy.http_client = http_client
        return copy

    def add_post_response_hook(self, hooks, create_new=False):
        """Add a post response hook

        parser                  a function that is call when the response is completed.
                                This function will be called for any status code.
        create_new              if True a new RestAPI object is returned,
                                else the current one is modified (default: False)
        """
        copy = self.copy() if create_new else self
        copy.post_response_hooks.append(hooks)
        return copy

    def partial(self, create_new=False, **params):
        """Partially fill this api.

        create_new              if True a new RestAPI object is returned,
                                else the current one is modified (default: False)
        **params                fill the object with partial data.

        This is especially useful if you are creating multiple method for a single endpoint.
        """
        copy = self.copy() if create_new else self
        for key, param in six.iteritems(params):
            if key not in copy.params and key not in copy.url_params:
                raise RestAPIRuntimeException("Invalid params {0}".format(key))
            copy._partial_values[key] = param
        return copy

    def __call__(self, _retries_status=None, _max_tries=None, _cache=None, **params):
        """The actual call method

        _retries_status        The status to retry on. If not specified, use object default (self.retries_status)
        _max_tries             The number of time to retry. If not specified, use object default (self.max_tries)
        _cache                 Cache must be a tuple, (name_of_cache, time to cache (in minutes))

        Note: This will return a future, that needs to be yield.
        Returning a future here allows you to control when you yield it.
        Please call this with keyword arguments

        Note that if you use _cache, DO NOT modify the output

        """
        request = self._create_request(params=params)
        _retries_status = _retries_status if _retries_status is not None else self.retries_status
        _max_tries = _max_tries if _max_tries is not None else self.max_tries
        # return a coroutine
        return self._fetch_and_parse(request=request, retries_status=_retries_status, max_tries=_max_tries, cache=_cache)

    @tornado.gen.coroutine
    def _fetch_and_parse(self, request, retries_status, max_tries, cache):
        """Fetch and parse
        return the response, do not do any processing except parsing

        please call this with keyword arguments
        """
        if cache is not None:
            name_of_cache = cache[0]
            time_to_cache = cache[1]
            if name_of_cache in self.cache:
                cached_data = self.cache[name_of_cache]
                if cached_data["expiry"] < time.time():
                    self.cache.pop(name_of_cache, None)
                else:
                    response = cached_data["response"]
                    raise tornado.gen.Return(response)

        response = yield _fetch_with_retries(request=request, http_client=self.http_client,
            retries_status=retries_status, max_tries=max_tries)
        if hasattr(response, "body") and response.body is not None and self.decode is not None:
            response.decoded_body = response.body.decode(self.decode)

        if response.code != 200:
            logging.warn(("Request error:\nURL: {}\nMethod: {}\nCode: {}\nBody: {}").format(
                    response.request.url, response.request.method, response.code, response.body))

        for hook in self.post_response_hooks:
            hook(response)

        if cache is not None:
            cached_data = { "expiry" : time.time() + (60 * time_to_cache),
                    "response": response }
            self.cache[name_of_cache] = cached_data

        raise tornado.gen.Return(response)

    def request(self, **params):
        """Create a request with params
        """
        return self._create_request(params=params)

    def _create_request(self, params):
        """Internal method to create request
        """
        for param_key, _ in six.iteritems(params):
            if param_key in self._partial_values:
                raise RestAPIRuntimeException("param {0} have been fixed".format(param_key))

        actual_params = {}
        actual_params.update(self._default_values)
        actual_params.update(params)
        actual_params.update(self._partial_values)

        self._clean_and_check_if_ready(actual_params)
        url = self._parse_url_and_pop_params(actual_params)
        body = None
        # create the actual request
        _r = { "method": self.method, "headers": {} }
        _r["headers"].update(self.headers)

        if self.method in (RestAPI.GET, RestAPI.DELETE): # if method is GET or POST, url params are added to url
            url = tornado.httputil.url_concat(url, actual_params)
        else:
            if self.request_body_type == RestAPI.FORM:
                body = tornado.httputil.urlencode(actual_params)
            else:
                body = json.dumps(actual_params)
                _r["headers"]["content-type"] = "application/json"

        _r["url"] = url
        if self.auth_username is not None and self.auth_password is not None:
            _r["auth_username"] = self.auth_username
            _r["auth_password"] = self.auth_password

        if body is not None:
            _r["body"] = body

        request = tornado.httpclient.HTTPRequest(**_r)
        return request

    def _clean_and_check_if_ready(self, actual_params):
        """Check if the request is ready to be called

        raise RestAPIRuntimeException if not enough param is passed to create the request
        """
        if self.host is None:
            raise RestAPIRuntimeException("host is not set")
        for key, param in six.iteritems(self.params):
            if param.get("is_required") and key not in actual_params:
                raise RestAPIRuntimeException("param {0} is required".format(key))

            if actual_params.get(key) is not None:
                old_value = actual_params[key]
                new_value = self._check_type_and_value_for_param(key, old_value, param)
                actual_params[key] = new_value

        for key in list(actual_params.keys()):
            if key not in self.params and key not in self.url_params:
                raise RestAPIRuntimeException("{0} is not a valid param".format(key))

    def _check_type_and_value_for_param(self, key, value, param):
        if param.get("type") is not None:
            param_type = param.get("type")
            if param_type in RestAPI.PARAM_TYPES:
                if param_type == "string":
                    try:
                        value = str(value)
                    except ValueError:
                        raise RestAPIRuntimeException("{0} cannot be converted to a string".format(value))
                elif param_type == "int":
                    try:
                        value = int(value)
                    except ValueError:
                        raise RestAPIRuntimeException("{0} cannot be converted to a int".format(value))
                elif param_type == "float":
                    try:
                        value = float(value)
                    except ValueError:
                        raise RestAPIRuntimeException("{0} cannot be converted to a float".format(value))
                elif param_type == "dict":
                    if not isinstance(value, dict):
                        raise RestAPIRuntimeException("{0} is not a dictionary".format(value))
                elif param_type == "list":
                    if not isinstance(value, list):
                        raise RestAPIRuntimeException("{0} is not a list".format(value))
                elif param_type == "bool":
                    if not isinstance(value, bool):
                        raise RestAPIRuntimeException("{0} is not a boolean".format(value))
                elif param_type == "comma_string":
                    if isinstance(value, str):
                        pass
                    elif isinstance(value, list):
                        try:
                            value = ",".join(value)
                        except ValueError:
                            raise RestAPIRuntimeException("{0} cannot be converted to a comma separated string".format(value))
                elif param_type == "bool_string":
                    if isinstance(value, str):
                        value_lowered = value.lower()
                        if value_lowered not in {"true", "false"}:
                            raise RestAPIRuntimeException("{0} is not valid bool_string value".format(value))
                        value = value_lowered
                    elif isinstance(value, bool):
                        value = { True: "true", False: "false" }.get(value)
                    else:
                        raise RestAPIRuntimeException("{0} is not valid bool_string value".format(value))

                elif callable(param_type):
                    value = param_type(callable)

        if value is not None:
            if param.get("choices") is not None:
                if not value in param.get("choices"):
                    raise RestAPIRuntimeException("{0} not is not a valid value for {1}".format(value, key))

        return value

    def _parse_url_and_pop_params(self, actual_params):
        url_params = {}
        for param in self.url_params:
            if param not in actual_params:
                raise RestAPIRuntimeException("URL params {0} is required".format(param))
            url_params[param] = actual_params.pop(param)

        url = self.url.format(**url_params)
        return "{protocol}://{host}{url}".format(protocol=self.protocol, host=self.host, url=url)


def parse_json_if_status(status_code=None, key="parsed_body"):
    """A post response hooks that parsed the output to json

    status_code             the status_code to decide when to parse to json
    key                     the key to store the parsed response ( default: "parsed_body")

    this will parsed the body to the key "json_body"
    """
    status_code = status_code if status_code is not None else { 200 }
    def _parse(response):
        if response.code in status_code:
            if hasattr(response, "decoded_body"):
                body = response.decoded_body
            else:
                body = response.body
            response.json_body = json.loads(body)
        else:
            response.json_body = None
    return _parse
