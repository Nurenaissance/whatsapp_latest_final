"""simplecrm URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from django.urls.conf import include
from contacts import views as cviews
from interaction import views as inviews
from simplecrm import Register_login as Reg
from simplecrm import ingestexcel as ingex
from simplecrm import get_column_name as getxcol
from simplecrm import get_user as getuser
from tenant import views as tenview
from node_temps import views as nviews
from dynamic_entities import views as dyv
from simplecrm import views as simviews
from custom_fields import views as cfviews
from analytics import views as analyticsviews
from helpers import  vectorize
from helpers import upload_dispatch as u_dispatch
from custom_fields.views import export_data_for_custom_field as edfc
from topicmodelling import views as topicviews
from whatsapp_chat import views as wa_chat_views, message_stats
from rest_framework.routers import DefaultRouter
from communication import insta_msg as imsg 
from communication import views as commviews
from communication import sentiment as commsenti
from shop import views as shop_views
from helpers import tables
from orders import views as orderviews
from whatsapp_campaigns.views import WhatsappCampaignView


router = DefaultRouter()
router.register(r'groups', inviews.GroupViewSet, basename='group')

urlpatterns = router.urls


urlpatterns = [
    #path('admin/', admin.site.urls),
    path('register/', Reg.register, name='register'),  # Endpoint for user registration
    path('login/', Reg.LoginView.as_view(), name='login'), 
    path('contacts/', cviews.ContactListCreateAPIView.as_view(), name='contact-list-create'),
    path('get-contacts/', cviews.get_contacts_sql),
    path('contacts/<int:pk>/', cviews.ContactDetailAPIView.as_view(), name='contact-detail'),
    path('contacts_by_tenant/', cviews.ContactByTenantAPIView.as_view(), name='contact-by-tenant'),
    path('update-contacts/', cviews.UpdateContactAPIView.as_view(), name="update-contact-add-bgid"),
    path('excel-column/', getxcol.get_excel_columns, name='column_excel'),
    path('get-user/<str:username>/', getuser.get_user_by_username, name='get_user'),
    path('get-all-user/', getuser.get_all_users, name='get_all_user'),
    path('createTenant/', tenview.tenant_list, name='tenant'),
    path('verifyTenant/', tenview.verify_tenant, name='verify-tenant'),
    path('logout/', Reg.LogoutView.as_view(), name='logout'),
    path(r'node-templates/', nviews.NodeTemplateListCreateAPIView.as_view(), name='node-template-list-create'),
    path('node-templates/<int:pk>/', nviews.NodeTemplateDetailAPIView.as_view(), name='node-template-detail'),
    path('create-dynamic-model/', dyv.CreateDynamicModelView.as_view(), name='create_dynamic_model'),
    path('dynamic-models/', dyv.DynamicModelListView.as_view(), name='dynamic_model_list'),
    path('dynamic-model-data/<str:model_name>/', dyv.DynamicModelDataView.as_view(), name='dynamic_model_data'),
    path('delete-dynamic-model/<str:model_name>/', dyv.DeleteDynamicModelView.as_view(), name='delete_dynamic_model'),
    path('deduplicate/', simviews.deduplicate_view, name='deduplicate'),
    path('create-custom-field/', cfviews.create_custom_field, name='create_custom_field'),
    path('whatsapp_convo_post/<str:contact_id>/', inviews.save_conversations, name='save_whatsapp_convo'),
    path('whatsapp_convo_get/<str:contact_id>/',inviews.view_conversation, name='get_whatsapp_convo'),
    path('contacts_of_account/<int:account_id>/',cviews.ContactByAccountAPIView.as_view(), name='contacts-by-account'),
    path('contacts-by-phone/<int:phone>/', cviews.ContactByPhoneAPIView.as_view(), name='contacts-by-phone'),
    path('delete-contact/<str:phone_number>/', cviews.delete_contact_by_phone, name='delete_contact_by_phone'),
    path('topic-modelling/<str:conversation_id>/', topicviews.topic_modelling_view, name='topic_modelling'),
    path('get-topic-modelling/<int:contact_id>/', topicviews.TopicModellingView.as_view(), name='topic-modelling-get'),
    path('insert-data/', wa_chat_views.insert_whatsapp_tenant_data),
    path('whatsapp_tenant/', wa_chat_views.get_whatsapp_tenant_data),
    # path('save-messages/', imsg.save_messages, name='save-messages'),  # Save messages
    path('set-status/', wa_chat_views.update_message_status),
    path('get-status/', wa_chat_views.get_status),
    path('conversations/', commviews.ConversationListCreateView.as_view(), name='conversation-list-create'),
    path('conversations/<int:pk>/', commviews.ConversationDetailView.as_view(), name='conversation-detail'),
    path('upload/', u_dispatch.dispatcher, name='upload_dispatch'),
    # whatsapp interaction to message
    # path('save_whatsapp_conversations/', inviews.save_whatsapp_conversations_to_messages, name='save_interaction_conversations'),
    path('group-messages/', commviews.GroupMessagesView.as_view(), name='group_messages'),# all message to conversations
    path('get-tenant/', wa_chat_views.get_tenant),
    path('api/sentiment-analysis/conversation/<str:conversation_id>/', commsenti.analyze_sentiment_for_conversation, name='analyze_sentiment'),
    path('user-data/', analyticsviews.userCreateListView.as_view(), name='add-user-data'),
    path('query-faiss/', vectorize.query , name='query-into-faiss-data'),\
    path('whatsapp-media-uploads/', vectorize.handle_media_uploads , name="return_json_object"),
    path('update-last-seen/<str:phone>/<str:type>', cviews.updateLastSeen),
    path('verifyTenant/', tenview.verify_tenant, name='verify-tenant'),
    path('catalog-id/', tenview.add_catalog_id),
    path('change-password/', Reg.change_password, name ='change-password'),
    path('catalog/', shop_views.ShopListCreateAPIView.as_view()),
    path('process-order/', shop_views.process_order, name='process-order'),
    path('create-spreadsheet/', shop_views.create_spreadsheets, name='create spreadsheets'),
    path('query/', vectorize.handle_query, name="query-into-db"),
    path('upload-doc/', vectorize.vectorize),
    path("add-key/<str:tenant_id>/", tenview.add_key, name="add_key"),
    path('prompt-to-flow/', tables.test),
    path('translate-flow/', wa_chat_views.translate_whatsapp_flow),
    path('test-api/', wa_chat_views.test_api),
    path('product-bulk-upload/', shop_views.ProductUploadView.as_view()),

    path('retailers/create/', orderviews.RetailerCreateAPIView.as_view(), name='retailer-create'),
    path('retailers/update/<int:pk>/', orderviews.RetailerUpdateAPIView.as_view(), name='retailer-update'),
    path('retailers/delete/<int:pk>/', orderviews.RetailerDeleteAPIView.as_view(), name='retailer-delete'),
    path('retailers/', orderviews.RetailerListAPIView.as_view(), name='retailer-list'),
    path('retailers/<int:pk>/', orderviews.RetailerDetailAPIView.as_view(), name='retailer-detail'),

    path('orders/create/', orderviews.OrderCreateAPIView.as_view(), name='order-create'),
    path('orders/update/<int:pk>/', orderviews.OrderUpdateAPIView.as_view(), name='order-update'),
    path('orders/delete/<int:pk>/', orderviews.OrderDeleteAPIView.as_view(), name='order-delete'), 
    path('orders/', orderviews.OrderListAPIView.as_view(), name='order-list'),
    path('orders/<int:pk>/', orderviews.OrderDetailAPIView.as_view(), name='order-detail'),
    path('campaign/', WhatsappCampaignView.as_view(), name='campaign_api'),
    path('message-stat/', message_stats.MessageStatisticsView.as_view(), name = 'message_statistics'),
    path('individual_message_statistics/', message_stats.IndividualMessageStatisticsView.as_view(), name='individual_message_statistics_list'),  # For listing and creating
    
]
urlpatterns += router.urls