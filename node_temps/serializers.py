from rest_framework import serializers
from .models import NodeTemplate

class NodeTemplateSerializer(serializers.ModelSerializer):
    class Meta:
        model = NodeTemplate
        fields = "__all__"


    #cleanup funciton to include only one start node in the flow
    def cleanup(self, node_data):
            nodes = node_data.get('nodes', [])
            edges = node_data.get('edges', [])
            start_nodes = []
            start_edges = []

            for node in nodes:
                if(node['id'] == 'start'):
                    start_nodes.append(node)

            for edge in edges:
                if(edge['source'] == 'start'):
                    start_edges.append(edge)
            
            print("nodes: \n", start_nodes)
            print("edges: \n", start_edges)
            for node in start_nodes[1:]:
                nodes.remove(node)
            for edge in start_edges[1:]:
                edges.remove(edge)
            
            node_data['nodes'] = nodes
            node_data['edges'] = edges

            return node_data
    
    def create(self, validated_data):
        node_data = validated_data.get('node_data', {})
        validated_data['node_data'] = self.cleanup(node_data)
        return super().create(validated_data)
    
    def update(self, instance, validated_data):
        node_data = validated_data.get('node_data', instance.node_data)
        validated_data['node_data'] = self.cleanup(node_data)
        return super().update(instance, validated_data)
    
    

