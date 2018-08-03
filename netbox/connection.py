import requests
import socket
from netbox import exceptions


class NetboxConnection(object):

    def __init__(self, ssl_verify=False, use_ssl=True, host=None, auth_token=None, auth=None,
                 port=80, api_prefix=None):
        self.use_ssl = use_ssl
        self.host = host
        self.auth_token = auth_token
        self.port = port
        self.auth = auth
        self.api_prefix = api_prefix

        if use_ssl:
            self.port = 443

        self.base_url = 'http{s}://{host}:{p}{prefix}'.format(s='s' if use_ssl else '', p=self.port, host=self.host,
                                                               prefix='/api' if api_prefix is None else api_prefix)

        self.ssl_verify = ssl_verify
        self._session = None

        # self.session = requests.Session()
        # self.session.verify = ssl_verify

        # if auth:
        #     self.session.auth = auth
        #
        # if auth_token:
        #     token = 'Token {}'.format(self.auth_token)
        #     self.session.headers.update({'Authorization': token})
        #     self.session.headers.update({'Accept': 'application/json'})
        #     self.session.headers.update({'Content-Type': 'application/json'})
        #
        # if auth and auth_token:
        #     raise ValueError('Only one authentication method is possible. Please use auth or auth_token')

    @property
    def session(self):
        print('entering session')
        if not self._session:
            self._connect()
        return self._session

    def _connect(self):

        sess = requests.Session()
        sess.verify = self.ssl_verify

        if self.auth:
            sess.auth = self.auth

        if self.auth_token:
            token = 'Token {}'.format(self.auth_token)
            sess.headers.update({'Authorization': token})
            sess.headers.update({'Accept': 'application/json'})
            sess.headers.update({'Content-Type': 'application/json'})

        if self.auth and self.auth_token:
            raise ValueError('Only one authentication method is possible. Please use auth or auth_token')

        print('entering _connect')
        print(sess)
        self._session = sess

    def __request(self, method, params=None, key=None, body=None, url=None):

        if method != 'GET':
            if not self.auth_token:
                raise exceptions.AuthException('Authentication credentials were not provided')

            if self.auth:
                raise exceptions.AuthException('With basic authentication the API is not writable.')

        if url is None:
            if key is not None:
                url = self.base_url + str(params) + str('{}/'.format(key))
            else:
                url = self.base_url + str(params)

        request = requests.Request(method=method, url=url, json=body)
        print(self._session)
        prepared_request = self.session.prepare_request(request)
        print(prepared_request)

        try:
            response = self.session.send(prepared_request)
        except socket.gaierror:
            raise socket.gaierror('Unable to find address: {}'.format(self.host))
        except requests.exceptions.ConnectionError:
            raise ConnectionError('Unable to connect to Netbox host: {}'.format(self.host))
        except requests.exceptions.Timeout:
            raise TimeoutError('Connection to Netbox host timed out')
        except Exception as e:
            raise Exception(e)
        finally:
            self.close()

        try:
            response_data = response.json()
        except:
            response_data = response.content

        return response.ok, response.status_code, response_data

    def get(self, param, key=None, **kwargs):
        if kwargs:
            url = '{}{}?{}'.format(self.base_url, param,
                                   '&'.join('{}={}'.format(key, val) for key, val in kwargs.items()))
        elif key:
            url = '{}{}/?q={}'.format(self.base_url, param, key)
        else:
            url = '{}{}'.format(self.base_url, param)

        resp_ok, resp_status, resp_data = self.__request('GET', params=param, key=key, url=url)

        if resp_ok and resp_status == 200:
            if 'results' in resp_data:
                return resp_data['results']
            else:
                return resp_data
        else:
            return []

    def put(self, params):

        return self.__request('PUT', params)

    def patch(self, params, key, **kwargs):

        body_data = {key: value for (key, value) in kwargs.items()}
        resp_ok, resp_status, resp_data = self.__request('PATCH', params=params, key=key, body=body_data)

        if resp_ok and resp_status == 200:
            return True
        else:
            raise exceptions.UpdateException(resp_data)

    def post(self, params, required_fields, **kwargs):

        body_data = {key: value for (key, value) in required_fields.items()}

        if kwargs:
            body_data.update({key: value for (key, value) in kwargs.items()})

        resp_ok, resp_status, resp_data = self.__request('POST', params=params, body=body_data)

        if resp_ok and resp_status == 201:
            return True
        else:
            raise exceptions.CreateException(resp_data)

    def delete(self, params, del_id):

        del_str = '{}{}'.format(params, del_id)
        resp_ok, resp_status, resp_data = self.__request('DELETE', del_str)

        if resp_ok and resp_status == 204:
            return True
        else:
            raise exceptions.DeleteException(resp_data)

    def close(self):

        self.session.close()