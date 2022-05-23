# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

import intercom_pb2 as intercom__pb2


class InvoiceStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Pay = channel.unary_unary(
                '/Invoice/Pay',
                request_serializer=intercom__pb2.PayRequest.SerializeToString,
                response_deserializer=intercom__pb2.PayResponse.FromString,
                )


class InvoiceServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Pay(self, request, context):
        """Missing associated documentation comment in .proto file."""
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_InvoiceServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Pay': grpc.unary_unary_rpc_method_handler(
                    servicer.Pay,
                    request_deserializer=intercom__pb2.PayRequest.FromString,
                    response_serializer=intercom__pb2.PayResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Invoice', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Invoice(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Pay(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Invoice/Pay',
            intercom__pb2.PayRequest.SerializeToString,
            intercom__pb2.PayResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)