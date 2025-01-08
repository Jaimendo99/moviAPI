from movi_payload_decode import decode_payload, encode_payload
from httpx import AsyncClient, Response
import asyncio
import pickle
import copy


class MoviCookies:
    def __init__(self, cookies, cfadmin):
        self.cookies = cookies
        self.cfadmin = cfadmin


class MovistarClient:
    def __init__(self):
        self.base_url = "https://fullstack.movistar.com.ec/"
        movicookies = self.login()
        self.cookies = movicookies.cookies
        self.cfadmin = movicookies.cfadmin

    def login(self) -> MoviCookies:
        session_cookies = ''
        cookie_movistar = pickle.loads(
            open("cookies-movistar.pkl", "rb").read())
        for cookie in cookie_movistar:
            session_cookies += f"{cookie['name']}={cookie['value']};"

        cfadmin = pickle.loads(
            open("cfadmin-movistar.pkl", "rb").read())['cfadmin']

        return MoviCookies(session_cookies, cfadmin)

    async def get_client(self, async_client: AsyncClient, requestPayload: dict) -> Response:
        headers = {
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }
        return await async_client.post(self.base_url + "rest/UIPlugins/WidgetRequestProcessor/process", headers=headers, data=requestPayload)

    async def get_clients(self, async_client: AsyncClient, info_list, info_type='id_number', info_rule='contiene') -> list[Response]:
        with open('searchPayload.txt', 'r') as file:
            searchPayload = file.read()

        searchPayloadDict = decode_payload(searchPayload)

        requests = []
        for info in info_list:
            print(info, info_type, info_rule)
            if info_type == 'id_number':
                searchPayloadItem = self._build_payload(
                    searchPayloadDict.copy(), id_number=info, id_rule=info_rule)

            elif info_type == 'phone_number':
                searchPayloadItem = self._build_payload(
                    searchPayloadDict.copy(), phone_number=info, pn_rule=info_rule)

            elif info_type == 'name':
                searchPayloadItem = self._build_payload(
                    searchPayloadDict.copy(), name=info, name_rule=info_rule)

            else:
                raise ValueError(f"Invalid search type {info_type}")

            requests.append(self.get_client(
                async_client, encode_payload(copy.deepcopy(searchPayloadItem))))

        return await asyncio.gather(*requests)

    async def get_line_info(self, async_client: AsyncClient, custumerId: str, contextId: str) -> Response:
        endpoint = "/csrd/rest/api/data/page"

        payload = {
            "pageDataRequest": {
                "pageToken": "!board",
                "params": {
                    "customerId": custumerId,
                    "contextId": contextId
                },
            },
        }
        headers = {
            'Content-Type': 'application/json; charset=UTF-8',
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }

        return await async_client.post(self.base_url + endpoint, headers=headers, json=payload)

    async def get_lines_info(self, async_client: AsyncClient, custumerId: list, contextId: list) -> list[Response]:
        if len(custumerId) != len(contextId):
            raise ValueError(
                "custumerId and contextId must have the same length")
        requests = [self.get_line_info(async_client, custumer, context)
                    for custumer, context in zip(custumerId, contextId)]
        return await asyncio.gather(*requests)

    async def get_custumer_info(self, async_client: AsyncClient, cutumerId: str, requests:list[str]= ['portin','portout','hostorial']) -> Response:
        endpoint = 'rest/UIPlugins/WidgetRequestProcessor/process'

        pass
        
    def __build_custumer_payload(self, requests:list[str]= ['portin','portout','hostorial'])->str:
        pass

    def _build_payload(
        self, payloadcopy: dict,
        phone_number: str = '',
            pn_rule: str = 'contiene',
            id_number: str = '',
            id_rule: str = 'contiene',
            name: str = '',
            name_rule: str = 'contiene'
    ) -> str:

        search_field_id = {'phone_number': '9146583874513687177',
                           'id_number': '9147380538313775291', 'names': '9132121613813866299'}
        search_rules = {'contiene': 'in', 'termina con': 'ew',
                        'se inicia con': 'sw', 'igual': 'eq'}

        if pn_rule not in search_rules or id_rule not in search_rules or name_rule not in search_rules:
            raise ValueError(f"Invalid search rule {pn_rule}")

        if phone_number == '' and id_number == '' and name == '':
            raise ValueError("At least one search field must be filled")

        searchs = {
            'phone_number': {'value': phone_number, 'rule': pn_rule},
            'id_number': {'value': id_number, 'rule': id_rule},
            'names': {'value': name, 'rule': name_rule}
        }

        searchCriteria = {
            'c': 'com.netcracker.platform.ui.plugins.gwt.search.shared.transport.SearchCriteria',
            'attributeId': '',
            'searchProfileId': '9145173674713662254',
            'searchRule': {'c': 'com.netcracker.platform.ui.plugins.gwt.search.shared.transport.field.SearchRule', 'code': '', 'text': ''},
            'values': [''],
            'searchMask': '*'
        }

        searchCriterias = []
        for key, value in searchs.items():
            searchCriteria_copy = searchCriteria.copy()
            if not value['value']:
                continue
            searchCriteria_copy['attributeId'] = search_field_id[key]
            searchCriteria_copy['searchRule']['code'] = search_rules[value['rule']]
            searchCriteria_copy['searchRule']['text'] = value['rule']
            searchCriteria_copy['values'] = [value['value']]
            searchCriterias.append(searchCriteria_copy)

        payloadcopy['requests'][0]['body']['requestParams']['SearchDescriptor']['searchCriterion'] = searchCriterias
        return payloadcopy
