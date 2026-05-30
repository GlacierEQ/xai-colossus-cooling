# ... [previous content]

    async def dispatch(self, req_dict: Dict[str, Any]) -> MCPResponse:
        # 1. Schema Validation (Issue #17)
        error = self.validate_request(req_dict)
        if error:
            return MCPResponse(
                request_id=req_dict.get('request_id', 'unknown'),
                request_type=req_dict.get('request_type', 'unknown'),
                status=ResponseStatus.ERROR,
                data={'status': 'ERROR', 'reason': f'Validation failed: {error}'}
            )
            
        req = MCPRequest(**req_dict)
        
        # 2. Forward to Orchestrator Tick Loop (Issue #16)
        if self._orchestrator and hasattr(self._orchestrator, 'event_queue'):
            await self._orchestrator.event_queue.put(req)

        logger.info('MCP dispatch [%s] req_id=%s', req.request_type, req.request_id)
        handler = self._handlers.get(req.request_type)
        if not handler:
            return MCPResponse(
                request_id=req.request_id,
                request_type=req.request_type,
                status=ResponseStatus.ERROR,
                data={'reason': f'No handler for {req.request_type}'},
            )
        try:
            data = await handler.handle(req)
            status = ResponseStatus.EMITTED if req.request_type == RequestType.EMERGENCY else ResponseStatus.OK
        except Exception as e:
            data = {'error': str(e)}
            status = ResponseStatus.ERROR
        resp = MCPResponse(
            request_id=req.request_id,
            request_type=req.request_type,
            status=status,
            data=data,
        )
        # 3. Async Logging (Issue #18)
        await aspen_logger.log_event(resp.__dict__)
        return resp
