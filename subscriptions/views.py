from django.shortcuts import render
from datetime import datetime
import requests, json, os, pytz, re, datetime, pytz
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from .models import Plan, Subscription
from tenant.models import Tenant
from django.db import DatabaseError, connection
from django.core.exceptions import ObjectDoesNotExist

def unix_to_datetime(unix_timestamp):
    """
    Convert a Unix timestamp to a Django-compatible timezone-aware DateTimeField.
    
    Args:
        unix_timestamp (int or None): The Unix timestamp in seconds.
    
    Returns:
        datetime or None: A timezone-aware datetime object or None if input is invalid.
    """
    if unix_timestamp is None:
        return None 
    
    india_tz = pytz.timezone('Asia/Kolkata')  # Define India Standard Time (IST)

    dt = datetime.datetime.fromtimestamp(unix_timestamp, india_tz)
    print("returning dt: ", dt)
    return dt


@csrf_exempt
def createSubscription(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            tenant_id = request.headers.get('X-Tenant-Id')
            plan_id = data.get('plan_id')

            subscription = create_razorpay_subscription(plan_id, 6, 1, customer_notify=1)

            
            print("Subscription created: ", subscription)

            Subscription2.objects.create(
                id=subscription['id'],
                tenant = tenant_id,
                past_payments = [],
                payment_url = subscription['short_url']
            )

            return JsonResponse(subscription, status=200)
        
        except json.JSONDecodeError:
            return JsonResponse({'error': 'Invalid JSON data'}, status=400)
        except requests.exceptions.RequestException as e:
            return JsonResponse({'error': str(e)}, status=500)
        except Exception as e:
            return JsonResponse({'error': f'An unexpected error occurred - {e}'}, status=500)
    
    else:
        return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)
    
# @csrf_exempt
# def createSubscription(request):
#     if request.method == 'POST':
#         try:
#             data = json.loads(request.body)
#             tenant_id = request.headers.get('X-Tenant-Id')
#             plan_id = data.get('plan_id')
#             period = data.get('period')
#             total_count = data.get('total_count', 1)
#             quantity = data.get('quantity', 1)
#             customer_notify = data.get('customer_notify') #0 for business, 1 for razorpay
#             start_at = data.get('start_at')

#             if period == "weekly":
#                 expire_by = start_at + 7*24*60*60*quantity
#             elif period == "monthly":
#                 expire_by = start_at + 30*24*60*60*quantity
#             elif period == "yearly":
#                 expire_by = start_at + 365*24*60*60*quantity
#             elif period == "daily":
#                 expire_by = start_at + 24*60*60*quantity

#             # addons = data.get('addons')
#             # offer_id = data.get('offer_id')
#             # notes = data.get('notes')
            
#             # if not all([plan_id, total_count, quantity, customer_notify, start_at, expire_by]):
#             #     print(plan_id, total_count, quantity, customer_notify, start_at, expire_by)
#             #     return JsonResponse({'error': 'Missing required fields'}, status=400)
            
#             subscription = create_razorpay_subscription( plan_id, total_count, quantity, customer_notify, start_at, expire_by)

#             print("Subscription created: ", subscription)

#             Subscription.objects.update_or_create(
#                 id=subscription['id'],
#                 defaults={
#                     'plan_id': subscription.get('plan_id', ''),
#                     'plan_name': Plan.objects.filter(id=plan_id).values_list("name", flat=True).first(),  # Replace with logic to fetch plan name if necessary
#                     'status': subscription.get('status', 'created'),
#                     'current_start': unix_to_datetime(subscription.get('current_start')),
#                     'current_end': unix_to_datetime(subscription.get('current_end')),
#                     'ended_at': unix_to_datetime(subscription.get('ended_at')),
#                     'notes': subscription.get('notes', []),
#                     'charge_at': unix_to_datetime(subscription.get('charge_at')),
#                     'start_at': unix_to_datetime(subscription.get('start_at')),
#                     'end_at': unix_to_datetime(subscription.get('end_at')),
#                     'total_count': subscription.get('total_count', 1),
#                     'paid_count': subscription.get('paid_count', 0),
#                     'remaining_count': subscription.get('remaining_count', 0),
#                     'customer_notify': subscription.get('customer_notify', True),
#                     'created_at': subscription.get('created_at', 0),
#                     'expire_by': unix_to_datetime(subscription.get('expire_by')),
#                     'short_url': subscription.get('short_url', ''),
#                     'has_scheduled_changes': subscription.get('has_scheduled_changes', False),
#                     'change_scheduled_at': unix_to_datetime(subscription.get('change_scheduled_at')),
#                     'source': subscription.get('source', 'api'),
#                     'offer_id': subscription.get('offer_id', None),
#                     'tenant': tenant_id
#                 }
#             )

#             return JsonResponse(subscription, status=200)
        
#         except json.JSONDecodeError:
#             return JsonResponse({'error': 'Invalid JSON data'}, status=400)
#         except requests.exceptions.RequestException as e:
#             return JsonResponse({'error': str(e)}, status=500)
#         except Exception as e:
#             return JsonResponse({'error': f'An unexpected error occurred - {e}'}, status=500)
    
#     else:
#         return JsonResponse({'error': 'Only POST requests are allowed'}, status=405)

API_KEY_ID = os.getenv("RAZORPAY_API_KEY")
API_KEY_SECRET = os.getenv('RAZORPAY_API_SECRET')

import base64
import requests

def create_razorpay_subscription(plan_id, total_count, quantity, customer_notify):
    try:
        url = "https://api.razorpay.com/v1/subscriptions"
        
        headers = {
            "Content-Type": "application/json",
        }
        
        payload = {
            "plan_id": plan_id,
            "total_count": total_count,
            "quantity": quantity,
            "customer_notify": customer_notify
        }
        print("trying:   ", payload)
        response = requests.post(url, auth=(API_KEY_ID, API_KEY_SECRET), headers=headers, json=payload)
        print(response.json())
        # Check if the response was successful
        if response.status_code == 200:
            return response.json()  # Return the response JSON if successful
        else:
            # Raise exception if status code is not 200 (OK)
            response.raise_for_status()
    
    except requests.exceptions.RequestException as e:
        # Catch any issues with the HTTP request (network, timeout, invalid response, etc.)
        print(f"Request error: {str(e)}")
        return {'error': f"Request error: {str(e)}"}
    
    except requests.exceptions.HTTPError as e:
        # Catch HTTP errors with status codes like 400, 500, etc.
        print(f"HTTP error: {str(e)}")
        return {'error': f"HTTP error: {str(e)}"}
    
    except Exception as e:
        # Catch any other unexpected errors
        print(f"Unexpected error: {str(e)}")
        return {'error': f"Unexpected error: {str(e)}"}
    

def fetch_plans():
    """
    Fetches plans from Razorpay API and stores them in the database.
    """
    url = "https://api.razorpay.com/v1/plans"
    
    
    response = requests.get(url, auth=(API_KEY_ID, API_KEY_SECRET))

    if response.status_code == 200:
        data = response.json()
        plans = data.get("items", [])

        for plan in plans:
            created_at = unix_to_datetime(plan["item"]["created_at"])
            Plan.objects.update_or_create(
                id=plan["id"],
                defaults={
                    "period": plan["period"],
                    "interval": plan["interval"],
                    "active": plan["item"]["active"],
                    "name": plan["item"]["name"],
                    "description": plan["item"].get("description", ""),
                    "amount": plan["item"]["amount"]/100,
                    "currency": plan["item"]["currency"],
                    "created_at": created_at
                }
            )
        
        return f"Successfully stored {len(plans)} plans!"
    
    else:
        return f"Error {response.status_code}: {response.text}"

def fetch_subscriptions():
    """Fetch subscriptions from Razorpay API and store/update them in the database."""
    url = 'https://api.razorpay.com/v1/subscriptions'

    try:
        response = requests.get(url, auth=(API_KEY_ID, API_KEY_SECRET))
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx, 5xx)

        data = response.json()
        subscriptions = data.get("items", [])

        for subscription in subscriptions:
            plan_id = subscription.get("plan_id")
            
            # status = subscription["status"]

            # if status == "expired":
            #     subscription_id = subscription["id"]
            #     try:
            #         subscription = Subscription.objects.get(id=subscription_id)
            #     except Subscription.DoesNotExist:
            #         # raise NotFound(detail="Subscription not found", code=404)
            #         print(f"Subscription {subscription_id} not found")
            #         continue
                
            #     subscription.delete()


            plan_name = Plan.objects.filter(id=plan_id).values_list("name", flat=True).first() or "Unknown Plan"

            Subscription.objects.update_or_create(
                id=subscription["id"],
                defaults={
                    "plan_id": plan_id,
                    "plan_name": plan_name,
                    "status": subscription.get("status", "created"),

                    # Convert timestamps
                    "current_start": unix_to_datetime(subscription.get("current_start")),
                    "current_end": unix_to_datetime(subscription.get("current_end")),
                    "ended_at": unix_to_datetime(subscription.get("ended_at")),
                    "charge_at": unix_to_datetime(subscription.get("charge_at")),
                    "start_at": unix_to_datetime(subscription.get("start_at")),
                    "end_at": unix_to_datetime(subscription.get("end_at")),
                    "change_scheduled_at": unix_to_datetime(subscription.get("change_scheduled_at")),

                    # Other fields
                    "total_count": subscription.get("total_count", 1),
                    "paid_count": subscription.get("paid_count", 0),
                    "remaining_count": subscription.get("remaining_count", 0),
                    "customer_notify": subscription.get("customer_notify", False),
                    "created_at": subscription.get("created_at", 0),
                    "expire_by": subscription.get("expire_by"),
                    "short_url": subscription.get("short_url", ""),
                    "has_scheduled_changes": subscription.get("has_scheduled_changes", False),
                    "source": subscription.get("source", "api"),
                    "offer_id": subscription.get("offer_id", ""),
                    "notes": subscription.get("notes", []),  # Ensure it's stored as JSON
                }
            )

        return f"Successfully updated {len(subscriptions)} subscriptions!"

    except requests.exceptions.RequestException as e:
        return f"Request error: {str(e)}"

    except Exception as e:
        return f"An unexpected error occurred: {str(e)}"

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Subscription, Plan, Subscription2
from .serializers import SubscriptionSerializer, PlanSerializer, Subscription2Serializer
from rest_framework.exceptions import NotFound

class SubscriptionDetailView(APIView):
    def get(self, request, subscription_id=None, format=None):
        tenant_id = request.headers.get('X-Tenant-Id')

        if tenant_id:
            try:
                subscription = Subscription.objects.get(tenant= tenant_id)
                serializer = SubscriptionSerializer(subscription)
                return Response(serializer.data)
            except Subscription.DoesNotExist:
                raise NotFound(detail="Subscription not found", code=404)
        else:
            subscriptions = Subscription.objects.all()
            serializer = SubscriptionSerializer(subscriptions, many=True)
            return Response(serializer.data)

    def delete(self, request, subscription_id, format=None):
        try:
            subscription = Subscription.objects.get(id=subscription_id)
        except Subscription.DoesNotExist:
            raise NotFound(detail="Subscription not found", code=404)
        
        subscription.delete()
        return Response({"message": "Subscription deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

class PlanDetailView(APIView):
    def get(self, request, plan_id=None, format=None):
        if plan_id:
            try:
                plan = Plan.objects.get(id=plan_id)
                serializer = PlanSerializer(plan)
                return Response(serializer.data)
            except Plan.DoesNotExist:
                raise NotFound(detail="Plan not found", code=404)
        else:
            plans = Plan.objects.all()
            serializer = PlanSerializer(plans, many=True)
            return Response(serializer.data)

    def delete(self, request, plan_id, format=None):
        try:
            plan = Plan.objects.get(id=plan_id)
        except Plan.DoesNotExist:
            raise NotFound(detail="Plan not found", code=404)
        

        plan.delete()
        return Response({"message": "Plan deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@csrf_exempt
def get_subscription(request):
    try:
        tenant_id = request.headers.get('X-Tenant-Id')
        query = """
                SELECT amount, created_at, expire_by
                FROM payments
                WHERE tenant_id = %s
                ORDER BY created_at DESC
                LIMIT 1
                """

        with connection.cursor() as cursor:
            cursor.execute(query, [tenant_id])
            result = cursor.fetchone()

        if not result:
            return JsonResponse({'success': False, 'error': 'No subscription found'}, status=404)

        amount, created_at, expire_by = result
        amount = int(amount)

        plan_mapping = {
            1499: {"planName": "Basic", "planId": "plan_Pon6Uno5uktIC4"},
            4999: {"planName": "Premium", "planId": "plan_Pon6DdCSMahsu7"},
            9999: {"planName": "Enterprise", "planId": "plan_Pon5wTJRvRQ0uC"},
        }
        
        plan_details = plan_mapping.get(amount, {"planName": "Unknown", "planId": "N/A"})

        days_remaining = (expire_by - datetime.datetime.now()).days if expire_by else None
        print("Days Remaining: ", days_remaining)

        response_data = {
            'success': True,
            'data': {
                'currentPlan': plan_details,
                'startDate': created_at,
                'nextBillingDate': expire_by,
                'daysRemaining': days_remaining,
            }
        }
        print(response_data)

        return JsonResponse(response_data)
    
    except Exception as e:
        print("Exception: ", e)
        return JsonResponse({"Error Occured": e}, status=500)

@csrf_exempt
def webhook(request):
    try:
        body_unicode = request.body.decode('utf-8')
        try:
            body_data = json.loads(body_unicode)
        except json.JSONDecodeError as e:
            print("Invalid JSON received:\n", request.body)
            return JsonResponse({"status": "error", "message": "Invalid JSON"}, status=400)

        event = body_data.get('event')
        if not event:
            print("Event not found in the payload")
            return JsonResponse({"status": "error", "message": "Event not found"}, status=400)
        
        print("Received event: ", body_data)

        if event == "payment.captured":
            try:
                payload = body_data.get("payload", {}).get("payment", {}).get("entity", {})
                if not payload:
                    raise ValueError("Missing payment entity in payload")

                ist = pytz.timezone("Asia/Kolkata")
                created_at_utc = datetime.datetime.utcfromtimestamp(payload.get("created_at", datetime.datetime.utcnow().timestamp()))
                created_at_ist = created_at_utc.replace(tzinfo=pytz.utc).astimezone(ist)
                created_at_str = created_at_ist.strftime('%Y-%m-%d %H:%M:%S')


                notes = payload.get("notes", {})
                org_name = notes.get("organization_name")
                email = notes.get("email")
                phone = notes.get("phone")
                amount = (payload.get("amount") or 0) / 100
                currency = payload.get("currency")
                status = payload.get("status")
                order_id = payload.get("order_id")
                pay_method = payload.get("method")
                description = payload.get("description")
                created_at = payload.get("created_at")
                payment_id = payload.get("id")

                if not org_name or not email or not phone or not amount:
                    raise ValueError("Missing required payment details")

                print("Org name: ", org_name)
                print("email: ", email)
                print("phone: ", phone)

                normalized_org_name = re.sub(r'\s+', ' ', org_name.strip()).lower()
                tenant = Tenant.objects.filter(organization__iexact=normalized_org_name).first()
                tenant_id = None
                if tenant:
                    if amount == 149900:
                        tenant.tier = "basic"
                        tenant_id = tenant.id
                    elif amount == 499900:
                        tenant.tier = "premium"
                        tenant_id = tenant.id
                    elif amount == 999900:
                        tenant.tier = "enterprise"
                        tenant_id = tenant.id
                    else:
                        print("Unrecognized amount: ", amount)
                        tenant_id = tenant.id

                    tenant.save()
                else:
                    print(f"Tenant not found for organization: {org_name}")
                    return JsonResponse({"status": "error", "message": "Tenant not found"}, status=404)
                
                with connection.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO payments (
                            payment_id, tenant_id, amount, currency, status, order_id, 
                            pay_method, email, contact, org_name, description, created_at
                        ) VALUES (
                            %s, %s, %s, %s, %s, %s, 
                            %s, %s, %s, %s, %s, %s
                        )
                    """, [
                        payment_id, tenant_id, amount, currency, status, order_id,
                        pay_method, email, phone, org_name, description, created_at_str
                    ])

                print("Payment event recorded successfully")
                return JsonResponse({"status": "success", "message": "Payment recorded"}, status=200)

            except ValueError as e:
                print(f"Error processing payment: {e}")
                return JsonResponse({"status": "error", "message": str(e)}, status=400)
            except ObjectDoesNotExist as e:
                print(f"Tenant lookup failed: {e}")
                return JsonResponse({"status": "error", "message": "Tenant not found"}, status=404)
            except DatabaseError as e:
                print(f"Database error: {e}")
                return JsonResponse({"status": "error", "message": "Database error"}, status=500)
            except Exception as e:
                print(f"Unexpected error: {e}")
                return JsonResponse({"status": "error", "message": "Unexpected error"}, status=500)

        return JsonResponse({"status": "success", "message": "Received"}, status=200)

    except Exception as e:
        print(f"Error processing webhook: {e}")
        return JsonResponse({"status": "error", "message": "Internal server error"}, status=500)

import schedule

def daily_task():
    current_time = datetime.datetime.now()

    with connection.cursor() as cursor:
        cursor.execute("""
            SELECT tenant_id, expire_by FROM payments
            WHERE expire_by > %s
        """, [current_time.strftime('%Y-%m-%d %H:%M:%S')])
        tenants = cursor.fetchall()

    for tenant in tenants:
        tenant_id, expire_by_str = tenant
        expire_by = datetime.datetime.strptime(expire_by_str, '%Y-%m-%d %H:%M:%S')

        print(f"Tenant {tenant_id} has an active subscription (expire_by: {expire_by})")

    if not tenants:
        print("No tenants with active subscriptions found.")


schedule.every().day.at("00:00:00").do(daily_task)
