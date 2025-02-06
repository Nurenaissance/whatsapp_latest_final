from django.forms.models import model_to_dict
import json, requests
from django.views import View
from .models import Flows
from django.http import JsonResponse
from whatsapp_chat.models import WhatsappTenantData
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator

@method_decorator(csrf_exempt, name='dispatch')
class FlowsView(View):
    def get(self, request, flow_id=None):
        tenant_id = request.headers.get('X-Tenant-Id')
        
        if flow_id:
            flow = Flows.objects.filter(id = flow_id, tenant = tenant_id)
            return JsonResponse(flow, status = 200)
        else:
            flows = Flows.objects.filter(tenanat = tenant_id)
            return JsonResponse(flows, status = 200)
    
    def post(self, request):
        tenant_id = request.headers.get('X-Tenant-Id')
        whatsapp_data = WhatsappTenantData.objects.filter(tenant_id = tenant_id).first()
        data = json.loads(request.body)

        name = data.get('name')
        categories = data.get('categories')
        flow_json = data.get('flow_json')
        publish = data.get('publish')
        
        if not name or not categories:
            return JsonResponse({"error": "Name and Categories are required"})

        data = {"name": name, "categories": categories, "flow_json": json.dumps(flow_json), "publish": publish}

        account_id = whatsapp_data.business_account_id
        access_token = whatsapp_data.access_token
        url = "https://graph.facebook.com/v22.0"

        response = requests.post(f"{url}/{account_id}/flows", data, headers={'Authorization': f"Bearer {access_token}"})
        
        if response.status_code == 200:
            try:
                response_data = response.json()
                flow = Flows.objects.create(
                    id = response_data.get('id', None),
                    name = name,
                    flow_json = flow_json or None,
                    publish = publish or False,
                    tenant_id = tenant_id
                )
                return JsonResponse(model_to_dict(flow), status=200, safe=False)
            except Exception as e:
                print("Exception Occured in POST/flows: ", e)
                return JsonResponse(e, safe=False)
        else:
            return JsonResponse(response.json(), safe=False)
