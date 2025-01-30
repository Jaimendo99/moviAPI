from movi_payload_decode import decode_payload, encode_payload
from httpx import AsyncClient, Response, Request
import asyncio
import pickle
import copy
import json
import re


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
                searchPayloadItem = self.__build_payload(
                    searchPayloadDict.copy(), id_number=info, id_rule=info_rule)

            elif info_type == 'phone_number':
                searchPayloadItem = self.__build_payload(
                    searchPayloadDict.copy(), phone_number=info, pn_rule=info_rule)

            elif info_type == 'name':
                searchPayloadItem = self.__build_payload(
                    searchPayloadDict.copy(), name=info, name_rule=info_rule)

            else:
                raise ValueError(f"Invalid search type {info_type}")

            requests.append(self.get_client(
                async_client, encode_payload(copy.deepcopy(searchPayloadItem))))

        return await asyncio.gather(*requests)

    async def get_line_info(self, async_client: AsyncClient, customerId: str, contextId: str) -> Response:
        endpoint = "/csrd/rest/api/data/page"

        payload = {
            "pageDataRequest": {
                "pageToken": "!board",
                "params": {
                    "customerId": customerId,
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

    async def get_lines_info(self, async_client: AsyncClient, customerId: list, contextId: list) -> list[Response]:
        if len(customerId) != len(contextId):
            raise ValueError(
                "custumerId and contextId must have the same length")
        requests = [self.get_line_info(async_client, custumer, context)
                    for custumer, context in zip(customerId, contextId)]
        return await asyncio.gather(*requests)

    async def get_customer_info(self, async_client: AsyncClient, customerId: str, requests: list[str] = ['portin', 'portout', 'hist']) -> Response:
        endpoint = 'rest/UIPlugins/WidgetRequestProcessor/process'
        headers = {
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }
        payload = self.__build_custumer_payload(requests)
        custumer_payload = payload.replace('@CUSTUMERID@', customerId)
        customer_payload_encode = encode_payload(json.loads(custumer_payload))

        return await async_client.post(self.base_url + endpoint, headers=headers, data=customer_payload_encode)

    async def get_custumers_info(self, async_client: AsyncClient, custumerIds: list[str], requests: list[str] = ['portin', 'portout', 'hist']) -> list[Response]:
        requests = [self.get_custumer_info(
            async_client, custumer, requests) for custumer in custumerIds]
        return await asyncio.gather(*requests)

    async def get_billing_info(self, async_client: AsyncClient, customerId: str, contextId: str, billingId: str, objectId: str) -> Response:
        endpoint = '/rest/UIPlugins/WidgetRequestProcessor/process'
        headers = {
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }
        payload = self.__build_payload_custom(
            'billing', customerId, contextId, billingId, objectId)

        return await async_client.post(self.base_url + endpoint, headers=headers, data=payload)

    async def get_billings(self, async_client: AsyncClient, customerId: list[str], contextId: list[str], billingIds: list[str], objectIds: list[str]) -> list[Response]:
        if len(customerId) != len(contextId) or len(customerId) != len(billingIds) or len(customerId) != len(objectIds):
            raise ValueError(
                "custumerId, contextId, billingId and objectId must have the same length")
        requests = [self.get_billing_info(async_client, custumer, context, billing, object)
                    for custumer, context, billing, object in zip(customerId, contextId, billingIds, objectIds)]
        return await asyncio.gather(*requests)

    async def get_address_info(self, async_client: AsyncClient, customerId: str, contextId: str, objectId: str, billingId: str) -> Response:
        endpoint = '/rest/UIPlugins/WidgetRequestProcessor/process'
        headers = {
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }
        payload = self.__build_payload_custom(
            'address', customerId, contextId, objectId, billingId)

        return await async_client.post(self.base_url + endpoint, headers=headers, data=payload)

    async def get_addresses(self, async_client: AsyncClient, customerId: list[str], contextId: list[str], objectIds: list[str], billingIds: list[str]) -> list[Response]:
        if len(customerId) != len(contextId) or len(customerId) != len(objectIds) or len(customerId) != len(billingIds):
            raise ValueError(
                "custumerId, contextId, objectId and billingId must have the same length")
        requests = [self.get_address_info(async_client, custumer, context, object, billing)
                    for custumer, context, object, billing in zip(customerId, contextId, objectIds, billingIds)]
        return await asyncio.gather(*requests)

    async def get_billing_account_info(self, async_client: AsyncClient, customerId: str, contextId: str, billingId: str, objectId: str, lineId: str) -> Response:
        endpoint = '/rest/UIPlugins/WidgetRequestProcessor/process'
        headers = {
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }
        payload = self.__build_payload_custom(
            'billing_account', customerId, contextId, billingId, objectId, lineId)

        return await async_client.post(self.base_url + endpoint, headers=headers, data=payload)

    async def get_billing_accounts(self, async_client: AsyncClient, customerId: list[str], contextId: list[str], billingIds: list[str], objectIds: list[str], lineIds: list[str]) -> list[Response]:
        if len(customerId) != len(contextId) or len(customerId) != len(billingIds) or len(customerId) != len(objectIds) or len(customerId) != len(lineIds):
            raise ValueError(
                "custumerId, contextId, billingId, objectId and lineId must have the same length")
        requests = [self.get_billing_account_info(async_client, custumer, context, billing, object, line)
                    for custumer, context, billing, object, line in zip(customerId, contextId, billingIds, objectIds, lineIds)]
        return await asyncio.gather(*requests)

    async def get_characteristics(self, async_client: AsyncClient, customerId: str, contextId: str, billingId: str, objectId: str) -> Response:
        endpoint = '/rest/UIPlugins/WidgetRequestProcessor/process'
        headers = {
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }
        payload = self.__build_payload_custom(
            'characteristics', customerId, contextId, billingId, objectId)
        return await async_client.post(self.base_url + endpoint, headers=headers, data=payload)

    async def get_characteristics_list(self, async_client: AsyncClient, customerId: list[str], contextId: list[str], billingIds: list[str], objectIds: list[str]) -> list[Response]:
        if len(customerId) != len(contextId) or len(customerId) != len(billingIds) or len(customerId) != len(objectIds):
            raise ValueError(
                "custumerId, contextId, billingId and objectId must have the same length")
        requests = [self.get_characteristics(async_client, custumer, context, billing, object)
                    for custumer, context, billing, object in zip(customerId, contextId, billingIds, objectIds)]
        return await asyncio.gather(*requests)

    async def get_product_intances(self, async_client: AsyncClient, customerId: str, contextId: str, billingId: str, objectId: str) -> Response:
        endpoint = '/rest/UIPlugins/WidgetRequestProcessor/process'
        headers = {
            'Cookie': self.cookies,
            'cfadmin': self.cfadmin,
        }
        payload = self.__build_payload_custom(
            'product', customerId, contextId, billingId, objectId)
        return await async_client.post(self.base_url + endpoint, headers=headers, data=payload)

    async def get_product_instances_list(self, async_client: AsyncClient, customerId: list[str], contextId: list[str], billingIds: list[str], objectIds: list[str]) -> list[Response]:
        if len(customerId) != len(contextId) or len(customerId) != len(billingIds) or len(customerId) != len(objectIds):
            raise ValueError(
                "custumerId, contextId, billingId and objectId must have the same length")
        requests = [self.get_product_intances(async_client, custumer, context, billing, object)
                    for custumer, context, billing, object in zip(customerId, contextId, billingIds, objectIds)]
        return await asyncio.gather(*requests)

    def __build_payload_custom(
            self, type: str, customerId: str, contextId: str, billingId: str, objectId: str, lineId: str = '') -> str:

        if type == 'billing':
            payload = '''
            request=%7B%22requests%22%3A%5B%7B%22path%22%3A%22%2Frest%2FUIPlugins%2FCtrl%2Frefresh%22%2C%22body%22%3A%22%7B%5C%22dsName%5C%22%3A%5C%22CBMCustomerBillingAccountListDS%5C%22%2C%5C%22objectPKs%5C%22%3A%5B%5C%22java.math.BigInteger%3A%7Bmot%3A2091641841013994133%3Bmas%3A1%3Bcontent%3A9149095206313263681%7D%5C%22%5D%2C%5C%22requestParams%5C%22%3A%7B%5C%22checkBoxEnabled%5C%22%3A%5C%22false%5C%22%2C%5C%22customizationEnabled%5C%22%3A%5C%22false%5C%22%2C%5C%22mask_field_resized%5C%22%3A%5C%22true%5C%22%2C%5C%22editable%5C%22%3Afalse%2C%5C%22modal_grid_panel%5C%22%3A%5C%22true%5C%22%2C%5C%22mergedWidgetContainerId%5C%22%3Anull%2C%5C%22gwtClass%5C%22%3A%5C%22com.netcracker.billingaiprovider.gwt.client.BAIPTableCtrl%5C%22%2C%5C%22coreDsId%5C%22%3A%5C%229135533240113270370%5C%22%2C%5C%22userViewHeaderEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22title%5C%22%3A%5C%22Cuentas%20de%20facturaci%C3%B3n%5C%22%2C%5C%22pagingEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22customizationColumnNumberEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22objectId%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22dashboardID%5C%22%3A%5C%229135533928813270800%5C%22%2C%5C%22widgetId%5C%22%3A%5C%229135559518513278429%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22initializationParams%5C%22%3A%7B%5C%22customizeReferenceFields%5C%22%3A%5C%22true%5C%22%2C%5C%22dashboardID%5C%22%3A%5C%229135533928813270800%5C%22%2C%5C%22referenceCustomizer%5C%22%3A%5C%22boardReferenceCustomizer%5C%22%2C%5C%22ncObjectID%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22csrdContext%5C%22%3A%7B%5C%22ctx_csrd_section_id%5C%22%3A%5C%22billingAccounts%5C%22%2C%5C%22ctx_csrd_page_token%5C%22%3A%5C%22!board%5C%22%2C%5C%22ctx_csrd_page_params%5C%22%3A%7B%5C%22customerId%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22sectionId%5C%22%3A%5C%22billingAccounts%5C%22%7D%2C%5C%22ctx_cihm_customer_id%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22ctx_csrd_filter_context_id%5C%22%3A%5C%221xidnkixu7hv7%5C%22%2C%5C%22ctx_csrd_page_host%5C%22%3A%5C%22%2Fcsrdesktop%2Fcsrdesktop.jsp%5C%22%2C%5C%22ctx_cihm_billing_account_id%5C%22%3A%5C%229149095190513612851%5C%22%7D%2C%5C%22showOperationsButton%5C%22%3A%5C%22true%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22objectPK%5C%22%3A%5C%22java.math.BigInteger%3A%7Bmot%3A0%3Bmas%3A1%3Bcontent%3A9149095206313263681%7D%5C%22%7D%2C%5C%22pageContext%5C%22%3A%5B%7B%5C%22name%5C%22%3A%5C%22cfadmin%5C%22%2C%5C%22value%5C%22%3A%5C%22oUPw-Jz0J-TmJX-mDIl-bnxV-tNdA%5C%22%7D%5D%2C%5C%22widgetContainerId%5C%22%3A%5C%229135559518513278430%5C%22%2C%5C%22hideEditableButton%5C%22%3Afalse%2C%5C%22urlParams%5C%22%3A%7B%7D%7D%2C%5C%22requestTimeout%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.model.shared.RequestTimeout%5C%22%2C%5C%22timeoutId%5C%22%3A%5C%22oJxMS1GZSip8YLKsNcF1idxV27oaxfj727IMEymbD3th85zUxa_9135559518513278430%5C%22%2C%5C%22v%5C%22%3A%5C%2220000%5C%22%7D%2C%5C%22pagingDescriptor%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.RequestPagingDescriptor%5C%22%2C%5C%22from%5C%22%3A0%2C%5C%22count%5C%22%3A10%2C%5C%22fullscreenCount%5C%22%3A0%7D%2C%5C%22filteringDescriptor%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.filtering.FilteringDescriptor%5C%22%2C%5C%22filters%5C%22%3A%7B%7D%7D%2C%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.rest.service.transport.request.TableCtrlRequest%5C%22%7D%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportRequest%22%7D%5D%2C%22groupTimeout%22%3A%22100000%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportGroupRequest%22%7D '''
        elif type == 'address':
            payload = '''
            request=%7B%22requests%22%3A%5B%7B%22path%22%3A%22%2Frest%2FUIPlugins%2FCtrl%2Frefresh%22%2C%22body%22%3A%22%7B%5C%22dsName%5C%22%3A%5C%22TfnLocationsPlatformTableCtrlDS%5C%22%2C%5C%22objectPKs%5C%22%3A%5B%5C%22java.math.BigInteger%3A%7Bmot%3A2091641841013994133%3Bmas%3A1%3Bcontent%3A9149095206313263681%7D%5C%22%5D%2C%5C%22requestParams%5C%22%3A%7B%5C%22checkBoxEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22customizationEnabled%5C%22%3A%5C%22false%5C%22%2C%5C%22mask_field_resized%5C%22%3A%5C%22true%5C%22%2C%5C%22modal_grid_panel%5C%22%3A%5C%22true%5C%22%2C%5C%22mergedWidgetContainerId%5C%22%3Anull%2C%5C%22gwtClass%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.client.TableCtrl%5C%22%2C%5C%22coreDsId%5C%22%3A%5C%229134660771413142816%5C%22%2C%5C%22pageSize%5C%22%3A%5C%2210%5C%22%2C%5C%22ncAttributes%5C%22%3A%5C%22-1%2C9132251685613889259%2C-2%5C%22%2C%5C%22userViewHeaderEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22title%5C%22%3A%5C%22Ubicaciones%20del%20cliente%5C%22%2C%5C%22pagingEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22customizationColumnNumberEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22objectId%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22dashboardID%5C%22%3A%5C%229144932611213850040%5C%22%2C%5C%22widgetId%5C%22%3A%5C%229144942818913865505%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22initializationParams%5C%22%3A%7B%5C%22customizeReferenceFields%5C%22%3A%5C%22true%5C%22%2C%5C%22dashboardID%5C%22%3A%5C%229144932611213850040%5C%22%2C%5C%22referenceCustomizer%5C%22%3A%5C%22boardReferenceCustomizer%5C%22%2C%5C%22ncObjectID%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22csrdContext%5C%22%3A%7B%5C%22ctx_csrd_section_id%5C%22%3A%5C%22locations%5C%22%2C%5C%22ctx_csrd_page_token%5C%22%3A%5C%22!board%5C%22%2C%5C%22ctx_csrd_page_params%5C%22%3A%7B%5C%22customerId%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22sectionId%5C%22%3A%5C%22locations%5C%22%7D%2C%5C%22ctx_cihm_customer_id%5C%22%3A%5C%229149095206313263681%5C%22%2C%5C%22ctx_csrd_filter_context_id%5C%22%3A%5C%221xidnkixu7hv7%5C%22%2C%5C%22ctx_csrd_page_host%5C%22%3A%5C%22%2Fcsrdesktop%2Fcsrdesktop.jsp%5C%22%2C%5C%22ctx_cihm_billing_account_id%5C%22%3A%5C%229149095190513612851%5C%22%7D%2C%5C%22showOperationsButton%5C%22%3A%5C%22true%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22objectPK%5C%22%3A%5C%22java.math.BigInteger%3A%7Bmot%3A0%3Bmas%3A1%3Bcontent%3A9149095206313263681%7D%5C%22%7D%2C%5C%22pageContext%5C%22%3A%5B%7B%5C%22name%5C%22%3A%5C%22cfadmin%5C%22%2C%5C%22value%5C%22%3A%5C%22oUPw-Jz0J-TmJX-mDIl-bnxV-tNdA%5C%22%7D%5D%2C%5C%22widgetContainerId%5C%22%3A%5C%229144932720113850181%5C%22%2C%5C%22editable%5C%22%3Atrue%2C%5C%22hideEditableButton%5C%22%3Afalse%2C%5C%22urlParams%5C%22%3A%7B%7D%7D%2C%5C%22requestTimeout%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.model.shared.RequestTimeout%5C%22%2C%5C%22timeoutId%5C%22%3A%5C%22bx8RWT19gWA4D1sznyldjEp2oMxgmKYKAZqOTHDGIpilTuHSaJ_9144932720113850181%5C%22%2C%5C%22v%5C%22%3A%5C%2220000%5C%22%7D%2C%5C%22pagingDescriptor%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.RequestPagingDescriptor%5C%22%2C%5C%22from%5C%22%3A0%2C%5C%22count%5C%22%3A10%2C%5C%22fullscreenCount%5C%22%3A0%7D%2C%5C%22filteringDescriptor%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.filtering.FilteringDescriptor%5C%22%2C%5C%22filters%5C%22%3A%7B%7D%7D%2C%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.rest.service.transport.request.TableCtrlRequest%5C%22%7D%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportRequest%22%7D%5D%2C%22groupTimeout%22%3A%22100000%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportGroupRequest%22%7D'''
        elif type == 'billing_account':
            if lineId == '':
                raise ValueError("lineId must be provided")
            payload = '''
            request=%7B%22requests%22%3A%5B%7B%22path%22%3A%22%2Frest%2FUIPlugins%2FCtrl%2Frefresh%22%2C%22body%22%3A%22%7B%5C%22dsName%5C%22%3A%5C%22CbmBaipPaymentMandateTransportDS%5C%22%2C%5C%22objectPKs%5C%22%3A%5B%5C%22java.math.BigInteger%3A%7Bmot%3A9135688263813316188%3Bmas%3A1%3Bcontent%3A9161251211263891063%7D%5C%22%5D%2C%5C%22requestParams%5C%22%3A%7B%5C%22customizationEnabled%5C%22%3A%5C%22false%5C%22%2C%5C%22mask_field_resized%5C%22%3A%5C%22true%5C%22%2C%5C%22editable%5C%22%3Afalse%2C%5C%22modal_grid_panel%5C%22%3A%5C%22true%5C%22%2C%5C%22mergedWidgetContainerId%5C%22%3Anull%2C%5C%22gwtClass%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.parctrl.client.ParCtrl%5C%22%2C%5C%22hideEditableButton%5C%22%3A%5C%22true%5C%22%2C%5C%22coreDsId%5C%22%3A%5C%229134229898013156551%5C%22%2C%5C%22userViewHeaderEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22title%5C%22%3A%5C%22Mandato%20de%20pago%5C%22%2C%5C%22customizationColumnNumberEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22objectId%5C%22%3A%5C%229161251211263891063%5C%22%2C%5C%22dashboardID%5C%22%3A%5C%229138014660013356148%5C%22%2C%5C%22widgetId%5C%22%3A%5C%229135819423513018254%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22initializationParams%5C%22%3A%7B%5C%22customizeReferenceFields%5C%22%3A%5C%22true%5C%22%2C%5C%22referenceCustomizer%5C%22%3A%5C%22boardReferenceCustomizer%5C%22%2C%5C%22forceReloadTabData%5C%22%3Atrue%2C%5C%22ncObjectID%5C%22%3A%5C%229161251211263891063%5C%22%2C%5C%22csrdContext%5C%22%3A%7B%5C%22ctx_csrd_section_id%5C%22%3A%5C%22billingAccounts%5C%22%2C%5C%22ctx_cihm_line_id%5C%22%3A%5C%229171636207513075116%5C%22%2C%5C%22ctx_csrd_page_token%5C%22%3A%5C%22!board%5C%22%2C%5C%22ctx_csrd_page_params%5C%22%3A%7B%5C%22customerId%5C%22%3A%5C%229161247913913899111%5C%22%2C%5C%22contextId%5C%22%3A%5C%221xojloz6zvj58%5C%22%2C%5C%22sectionId%5C%22%3A%5C%22billingAccounts%5C%22%2C%5C%22objectId%5C%22%3A%5C%229161251211263891063%5C%22%7D%2C%5C%22ctx_cihm_customer_id%5C%22%3A%5C%229161247913913899111%5C%22%2C%5C%22ctx_csrd_filter_context_id%5C%22%3A%5C%221xojloz6zvj58%5C%22%2C%5C%22ctx_csrd_page_host%5C%22%3A%5C%22%2Fcsrdesktop%2Fcsrdesktop.jsp%5C%22%2C%5C%22ctx_cihm_billing_account_id%5C%22%3A%5C%229171428407654120206%5C%22%7D%2C%5C%22showOperationsButton%5C%22%3A%5C%22true%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22objectPK%5C%22%3A%5C%22java.math.BigInteger%3A%7Bmot%3A0%3Bmas%3A1%3Bcontent%3A9161251211263891063%7D%5C%22%7D%2C%5C%22pageContext%5C%22%3A%5B%7B%5C%22name%5C%22%3A%5C%22cfadmin%5C%22%2C%5C%22value%5C%22%3A%5C%22oUPw-Jz0J-TmJX-mDIl-bnxV-tNdA%5C%22%7D%5D%2C%5C%22widgetContainerId%5C%22%3A%5C%229138014660013356151%5C%22%2C%5C%22urlParams%5C%22%3A%7B%7D%7D%2C%5C%22requestTimeout%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.model.shared.RequestTimeout%5C%22%2C%5C%22timeoutId%5C%22%3A%5C%22myRiTOiqgfJTyqOQ72PBDUe6GaRLour9GtPCgo88SScajxn6xH_9138014660013356151%5C%22%2C%5C%22v%5C%22%3A%5C%2220000%5C%22%7D%7D%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportRequest%22%7D%5D%2C%22groupTimeout%22%3A%22100000%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportGroupRequest%22%7D'''
        elif type == 'characteristics':
            payload = '''
            request=%7B%22requests%22%3A%5B%7B%22path%22%3A%22%2Frest%2FUIPlugins%2FCtrl%2Frefresh%22%2C%22body%22%3A%22%7B%5C%22dsName%5C%22%3A%5C%22LineItemCharacteristicsDS%5C%22%2C%5C%22objectPKs%5C%22%3A%5B%5C%22java.math.BigInteger%3A%7Bmot%3A9126083628313449001%3Bmas%3A1%3Bcontent%3A9161282613113642273%7D%5C%22%5D%2C%5C%22requestParams%5C%22%3A%7B%5C%22customizationEnabled%5C%22%3A%5C%22false%5C%22%2C%5C%22mask_field_resized%5C%22%3A%5C%22true%5C%22%2C%5C%22editable%5C%22%3Afalse%2C%5C%22modal_grid_panel%5C%22%3A%5C%22true%5C%22%2C%5C%22mergedWidgetContainerId%5C%22%3Anull%2C%5C%22gwtClass%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.parctrl.client.ParCtrl%5C%22%2C%5C%22hideEditableButton%5C%22%3A%5C%22true%5C%22%2C%5C%22coreDsId%5C%22%3A%5C%229134229898013156551%5C%22%2C%5C%22userViewHeaderEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22title%5C%22%3A%5C%22+%5C%22%2C%5C%22requestGrouping%5C%22%3A%5C%22true%5C%22%2C%5C%22customizationColumnNumberEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22requestGrouping_name%5C%22%3A%5C%22characteristics%5C%22%2C%5C%22objectId%5C%22%3A%5C%229161282613113642273%5C%22%2C%5C%22dashboardID%5C%22%3A%5C%229147879890013954875%5C%22%2C%5C%22widgetId%5C%22%3A%5C%229147879469813954580%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22initializationParams%5C%22%3A%7B%5C%22customizeReferenceFields%5C%22%3A%5C%22true%5C%22%2C%5C%22referenceCustomizer%5C%22%3A%5C%22boardReferenceCustomizer%5C%22%2C%5C%22forceReloadTabData%5C%22%3Atrue%2C%5C%22ncObjectID%5C%22%3A%5C%229161282613113642273%5C%22%2C%5C%22csrdContext%5C%22%3A%7B%5C%22ctx_csrd_section_id%5C%22%3A%5C%22salesOrders%5C%22%2C%5C%22ctx_csrd_page_token%5C%22%3A%5C%22!board%5C%22%2C%5C%22ctx_csrd_page_params%5C%22%3A%7B%5C%22customerId%5C%22%3A%5C%229149095206113030409%5C%22%2C%5C%22sectionId%5C%22%3A%5C%22salesOrders%5C%22%2C%5C%22objectId%5C%22%3A%5C%229161282613113642273%5C%22%7D%2C%5C%22ctx_cihm_customer_id%5C%22%3A%5C%229149095206113030409%5C%22%2C%5C%22ctx_csrd_filter_context_id%5C%22%3A%5C%221xidnl2ywfopi%5C%22%2C%5C%22ctx_csrd_page_host%5C%22%3A%5C%22%2Fcsrdesktop%2Fcsrdesktop.jsp%5C%22%2C%5C%22ctx_cihm_billing_account_id%5C%22%3A%5C%229149095234113467094%5C%22%7D%2C%5C%22showOperationsButton%5C%22%3A%5C%22true%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22objectPK%5C%22%3A%5C%22java.math.BigInteger%3A%7Bmot%3A0%3Bmas%3A1%3Bcontent%3A9161282613113642273%7D%5C%22%7D%2C%5C%22pageContext%5C%22%3A%5B%7B%5C%22name%5C%22%3A%5C%22cfadmin%5C%22%2C%5C%22value%5C%22%3A%5C%22V18Q-v103-7VIE-ItBN-t5KL-Ho6J%5C%22%7D%5D%2C%5C%22widgetContainerId%5C%22%3A%5C%229147879890013954886%5C%22%2C%5C%22urlParams%5C%22%3A%7B%7D%7D%2C%5C%22requestTimeout%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.model.shared.RequestTimeout%5C%22%2C%5C%22timeoutId%5C%22%3A%5C%22GHNvDrzOkDQVM7XEGkYKQxOy2XafassyamFqcIzvhjBHEaGuKb_9147879890013954886%5C%22%2C%5C%22v%5C%22%3A%5C%2220000%5C%22%7D%7D%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportRequest%22%7D%5D%2C%22groupTimeout%22%3A%22100000%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportGroupRequest%22%7D'''
        elif type == 'product':
            payload = '''
            request=%7B%22requests%22%3A%5B%7B%22path%22%3A%22%2Frest%2FUIPlugins%2FCtrl%2Frefresh%22%2C%22body%22%3A%22%7B%5C%22dsName%5C%22%3A%5C%22TableCtrlDynamicFetchPlanDS%5C%22%2C%5C%22objectPKs%5C%22%3A%5B%5C%22java.math.BigInteger%3A%7Bmot%3A9126083628313449001%3Bmas%3A1%3Bcontent%3A9149095393613527061%7D%5C%22%5D%2C%5C%22requestParams%5C%22%3A%7B%5C%22checkBoxEnabled%5C%22%3A%5C%22false%5C%22%2C%5C%22customizationEnabled%5C%22%3A%5C%22false%5C%22%2C%5C%22mask_field_resized%5C%22%3A%5C%22true%5C%22%2C%5C%22editable%5C%22%3Afalse%2C%5C%22modal_grid_panel%5C%22%3A%5C%22true%5C%22%2C%5C%22mergedWidgetContainerId%5C%22%3Anull%2C%5C%22gwtClass%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.client.TableCtrl%5C%22%2C%5C%22coreDsId%5C%22%3A%5C%229148285246313024943%5C%22%2C%5C%22pageSize%5C%22%3A%5C%2210%5C%22%2C%5C%22userViewHeaderEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22title%5C%22%3A%5C%22Instancias%20de%20producto%5C%22%2C%5C%22pagingEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22customizationColumnNumberEnabled%5C%22%3A%5C%22true%5C%22%2C%5C%22objectId%5C%22%3A%5C%229149095393613527061%5C%22%2C%5C%22dashboardID%5C%22%3A%5C%229148284980013024750%5C%22%2C%5C%22widgetId%5C%22%3A%5C%229134213657313166121%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22initializationParams%5C%22%3A%7B%5C%22customizeReferenceFields%5C%22%3A%5C%22true%5C%22%2C%5C%22referenceCustomizer%5C%22%3A%5C%22boardReferenceCustomizer%5C%22%2C%5C%22forceReloadTabData%5C%22%3Atrue%2C%5C%22ncObjectID%5C%22%3A%5C%229149095393613527061%5C%22%2C%5C%22csrdContext%5C%22%3A%7B%5C%22ctx_csrd_section_id%5C%22%3A%5C%22salesOrders%5C%22%2C%5C%22ctx_csrd_page_token%5C%22%3A%5C%22!board%5C%22%2C%5C%22ctx_csrd_page_params%5C%22%3A%7B%5C%22customerId%5C%22%3A%5C%229149095200313362696%5C%22%2C%5C%22sectionId%5C%22%3A%5C%22salesOrders%5C%22%2C%5C%22objectId%5C%22%3A%5C%229149095393613527061%5C%22%7D%2C%5C%22ctx_cihm_customer_id%5C%22%3A%5C%229149095200313362696%5C%22%2C%5C%22ctx_csrd_filter_context_id%5C%22%3A%5C%221xidnkkrzq7gw%5C%22%2C%5C%22ctx_csrd_page_host%5C%22%3A%5C%22%2Fcsrdesktop%2Fcsrdesktop.jsp%5C%22%2C%5C%22ctx_cihm_billing_account_id%5C%22%3A%5C%229149095194513651536%5C%22%7D%2C%5C%22showOperationsButton%5C%22%3A%5C%22true%5C%22%2C%5C%22drawFakeCheckboxes%5C%22%3A%5C%22false%5C%22%2C%5C%22objectPK%5C%22%3A%5C%22java.math.BigInteger%3A%7Bmot%3A0%3Bmas%3A1%3Bcontent%3A9149095393613527061%7D%5C%22%7D%2C%5C%22pageContext%5C%22%3A%5B%7B%5C%22name%5C%22%3A%5C%22cfadmin%5C%22%2C%5C%22value%5C%22%3A%5C%22V18Q-v103-7VIE-ItBN-t5KL-Ho6J%5C%22%7D%5D%2C%5C%22widgetContainerId%5C%22%3A%5C%229148285126113024874%5C%22%2C%5C%22hideEditableButton%5C%22%3Afalse%2C%5C%22urlParams%5C%22%3A%7B%7D%7D%2C%5C%22requestTimeout%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.model.shared.RequestTimeout%5C%22%2C%5C%22timeoutId%5C%22%3A%5C%22ODTTcD4z9B41JcFK5kYRnlzH3EtjBNp0P065eQ18RE6YZdOJVp_9148285126113024874%5C%22%2C%5C%22v%5C%22%3A%5C%2220000%5C%22%7D%2C%5C%22pagingDescriptor%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.RequestPagingDescriptor%5C%22%2C%5C%22from%5C%22%3A0%2C%5C%22count%5C%22%3A10%2C%5C%22fullscreenCount%5C%22%3A0%7D%2C%5C%22filteringDescriptor%5C%22%3A%7B%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.filtering.FilteringDescriptor%5C%22%2C%5C%22filters%5C%22%3A%7B%7D%7D%2C%5C%22c%5C%22%3A%5C%22com.netcracker.platform.ui.plugins.rest.service.transport.request.TableCtrlRequest%5C%22%7D%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportRequest%22%7D%5D%2C%22groupTimeout%22%3A%22100000%22%2C%22c%22%3A%22com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportGroupRequest%22%7D'''
        else:
            raise ValueError(f"Invalid type {type}")

        p_f = decode_payload(payload)

        d = str(p_f['requests'][0]['body']['objectPKs'])
        d2 = re.sub(r'content:\d+', f'content:{objectId}', d)
        p_f['requests'][0]['body']['objectPKs'] = eval(d2)
        p_f['requests'][0]['body']['requestParams']['objectId'] = objectId
        p_f['requests'][0]['body']['requestParams']['initializationParams']['ncObjectID'] = objectId
        p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_csrd_page_params']['customerId'] = customerId
        p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_cihm_customer_id'] = customerId
        p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_csrd_filter_context_id'] = contextId
        p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_cihm_billing_account_id'] = billingId
        d = str(p_f['requests'][0]['body']['requestParams']
                ['initializationParams']['objectPK'])
        d2 = re.sub(r'content:\d+', f'content:{objectId}', d)

        if type == 'billing_account':
            # nuevo de facturacion
            p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_cihm_line_id'] = lineId
            p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_csrd_page_params']['contextId'] = contextId
            p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_csrd_page_params']['objectId'] = objectId
        elif type == 'characteristics' or type == 'product':
            p_f['requests'][0]['body']['requestParams']['initializationParams']['csrdContext']['ctx_csrd_page_params']['objectId'] = objectId
            p_f['requests'][0]['body']['requestParams']['initializationParams']['objectPK'] = d2
        else:
            p_f['requests'][0]['body']['requestParams']['initializationParams']['objectPK'] = d2

        return encode_payload(p_f)

    def __build_custumer_payload(
            self, requests: list[str] = ['portin', 'portout', 'hist']) -> str:

        requests_header = {
            "requests": [],
            "groupTimeout": "100000",
            "c": "com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportGroupRequest"
        }

        request_catag = {
            'portin': {
                'cosreDsId': "9145243138113684909",
                'containerId': '9145244403913687320',
                'title': 'Solicitudes+de+Port-In',
            },
            'portout': {
                'cosreDsId': "9150197455813146054",
                'containerId': '9150197330013146017',
                'title': 'Solicitudes+de+Port-Out',
            },
            'hist': {
                'cosreDsId': "9157884230013223743",
                'containerId': '9157884230013223760',
                'title': 'Cambiar+Historial',
            }
        }

        request = {'path': '/rest/UIPlugins/Ctrl/refresh',
                   'body': {'dsName': 'DynamicPlatformTableCtrlDS',
                            'objectPKs': ['java.math.BigInteger:{mot:2091641841013994133;mas:1;content:@CUSTUMERID@}'],
                            'requestParams': {'checkBoxEnabled': 'false',
                                              'customizationEnabled': 'false',
                                              'mask_field_resized': 'true',
                                              'editable': False,
                                              'modal_grid_panel': 'true',
                                              'mergedWidgetContainerId': None,
                                              'gwtClass': 'com.netcracker.platform.ui.plugins.gwt.tablectrl.client.TableCtrl',
                                              'coreDsId': '9145553384013665894',
                                              'pageSize': '10',
                                              'userViewHeaderEnabled': 'true',
                                              'title': 'Entregables',
                                              'pagingEnabled': 'true',
                                              'customizationColumnNumberEnabled': 'true',
                                              'objectId': '@CUSTUMERID@',
                                              'dashboardID': '9139371752413211527',
                                              'widgetId': '9134213657313166121',
                                              'drawFakeCheckboxes': 'false',
                                              'initializationParams': {'customizeReferenceFields': 'true',
                                                                       'dashboardID': '9139371752413211527',
                                                                       'referenceCustomizer': 'boardReferenceCustomizer',
                                                                       'ncObjectID': '@CUSTUMERID@',
                                                                       'csrdContext': {'ctx_csrd_section_id': 'salesOrders',
                                                                                       'ctx_csrd_page_token': '!board',
                                                                                       'ctx_csrd_page_params': {'customerId': '@CUSTUMERID@',
                                                                                                                'sectionId': 'salesOrders'},
                                                                                       'ctx_cihm_customer_id': '@CUSTUMERID@',
                                                                                       'ctx_csrd_filter_context_id': '1xidnkkooi0bc',
                                                                                       'ctx_csrd_page_host': '/csrdesktop/csrdesktop.jsp',
                                                                                       'ctx_cihm_billing_account_id': '9149095194313394712'},
                                                                       'showOperationsButton': 'true',
                                                                       'drawFakeCheckboxes': 'false',
                                                                       'objectPK': 'java.math.BigInteger:{mot:0;mas:1;content:@CUSTUMERID@}'},
                                              'pageContext': [{'name': 'cfadmin',
                                                               'value': 'sLsl-gNu1-xNff-mnEt-lHDr-mjlQ'}],
                                              'widgetContainerId': '9145554285013667098',
                                              'hideEditableButton': False,
                                              'urlParams': {}},
                            'requestTimeout': {'c': 'com.netcracker.platform.ui.plugins.gwt.model.shared.RequestTimeout',
                                               'timeoutId': 'AxRtt193efLY1oaUZyGxcIVmizX5AY9MxaGytzQ39hAsk0ghfn_9145554285013667098',
                                               'v': '20000'},
                            'pagingDescriptor': {'c': 'com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.RequestPagingDescriptor',
                                                 'from': 0,
                                                 'count': 10,
                                                 'fullscreenCount': 0},
                            'filteringDescriptor': {'c': 'com.netcracker.platform.ui.plugins.gwt.tablectrl.shared.transport.filtering.FilteringDescriptor',
                                                    'filters': {}},
                            'c': 'com.netcracker.platform.ui.plugins.rest.service.transport.request.TableCtrlRequest'},
                   'c': 'com.netcracker.platform.ui.plugins.gwt.common.shared.transport.widget.request.WidgetTransportRequest'}

        requests_params = []
        for param in requests:
            param_copy = copy.deepcopy(request)
            if param == 'portin':
                param_copy['body']['requestParams']['coreDsId'] = request_catag['portin']['cosreDsId']
                param_copy['body']['requestParams']['widgetContainerId'] = request_catag['portin']['containerId']
                param_copy['body']['requestParams']['title'] = request_catag['portin']['title']
            if param == 'portout':
                param_copy['body']['requestParams']['coreDsId'] = request_catag['portout']['cosreDsId']
                param_copy['body']['requestParams']['widgetContainerId'] = request_catag['portout']['containerId']
                param_copy['body']['requestParams']['title'] = request_catag['portout']['title']
            if param == 'hist':
                param_copy['body']['requestParams']['coreDsId'] = request_catag['hist']['cosreDsId']
                param_copy['body']['requestParams']['widgetContainerId'] = request_catag['hist']['containerId']
                param_copy['body']['requestParams']['requestGrouping_name'] = 'changeHistory'
                param_copy['body']['requestParams']['title'] = request_catag['hist']['title']

            requests_params.append(param_copy)

        requests_header['requests'] = requests_params

        return json.dumps(requests_header)

    def __build_payload(
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
