<?php

class RestoModel_S5P extends RestoModel {

    public $extendedProperties = array(
        'absoluteOrbitNumber' => array(
            'name' => 'absoluteorbitnumber',
            'type' => 'NUMERIC'
        ),
        'frame' => array(
            'name' => 'frame',
            'type' => 'NUMERIC'
        ), 
        'cycle' => array(
            'name' => 'cycle',
            'type' => 'NUMERIC'
        ),
        'processingTime' => array(
            'name' => 'processingtime',
            'type' => 'TIMESTAMP'
        ),
        'baselineCollection' => array(
            'name' => 'baselinecollection',
            'type' => 'TEXT'
        )
    );

    /**
     * Constructor
     * 
     * @param RestoContext $context : Resto context
     * @param RestoContext $user : Resto user
     */
    public function __construct() {
        parent::__construct();
    }

    /**
     * Add feature to the {collection}.features table following the class model
     * 
     * @param array $data : array (MUST BE GeoJSON in abstract Model)
     * @param string $collectionName : collection name
     */
    public function storeFeature($data, $collectionName) {
        return parent::storeFeature($this->parse(join('',$data)), $collectionName);
    }

    /**
     * Update feature within {collection}.features table following the class model
     *
     * @param array $data : array (MUST BE GeoJSON in abstract Model)
     * @param string $featureIdentifier : the id of the feature (not obligatory)
     * @param string $featureTitle : the title of the feature (not obligatory)
     * @param RestoCollection $collection
     *
     */
    public function updateFeature($feature, $data) {
        return parent::updateFeature($feature, $this->parse(join('',$data)));
    }

    /**
     * Create JSON feature from xml string
     * 
     * @param {String} $xml : $xml string
     */
    private function parse($xml) {
        
        $dom = new DOMDocument();
        $dom->loadXML(rawurldecode($xml));
        
        /*
         * Computed from path
         */
        $path = trim($dom->getElementsByTagName('PATH')->item(0)->nodeValue);
        $explodedPath = explode('/', $path);
        $time = $dom->getElementsByTagName('ACQUISITION_TIME')->item(0);
        $orbits = $dom->getElementsByTagName('ORBIT_NUMBERS')->item(0);
        $processingInfo = $dom->getElementsByTagName('ESA_PROCESSING')->item(0);
        $zipFile = $dom->getElementsByTagName('ZIPFILE')->item(0);
        $polygon = RestoGeometryUtil::wktPolygonToArray(trim($dom->getElementsByTagName('ESA_TILEOUTLINE_FOOTPRINT_WKT')->item(0)->nodeValue));

	/*
         * Compatible with previous xml version
         */
        $instrument = trim($dom->getElementsByTagName('INSTRUMENT')->item(0)->nodeValue);
        if (empty($instrument)) {$instrument = $explodedPath[1];}
        $productType = trim($dom->getElementsByTagName('PRODUCT_TYPE')->item(0)->nodeValue);
        if (empty($productType)) {$productType = $explodedPath[2];}
        $processingLevel = trim($dom->getElementsByTagName('PROCESSING_LEVEL')->item(0)->nodeValue);
        if (empty($processingLevel)) {$processingLevel = 'LEVEL-1';}

	/*
	 * Not all products have frame number
	 */
	$frame = trim($orbits->getAttribute('frame'));
	if (empty($frame)){$frame = null;}
 
        /*
         * Initialize feature
         */
        $feature = array(
            'type' => 'Feature',
            'geometry' => array(
                'type' => 'Polygon',
                'coordinates' => array($polygon),
            ),
            'properties' => array(
                'productIdentifier' => trim($dom->getElementsByTagName('IDENTIFIER')->item(0)->nodeValue),
                'startDate' => RestoUtil::formatTimestamp(trim($time->getAttribute('start_datetime_utc'))),
                'completionDate' => RestoUtil::formatTimestamp(trim($time->getAttribute('stop_datetime_utc'))),
                'platform' =>  trim($dom->getElementsByTagName('SATELLITE')->item(0)->getAttribute('name')),
                'orbitNumber' => trim($orbits->getAttribute('relative')),
                'absoluteOrbitNumber' => trim($orbits->getAttribute('absolute')),
                'frame' => $frame,
                'cycle' => trim($orbits->getAttribute('cycle')),
                'resource' => $path,
                'resourceSize' => trim($zipFile->getAttribute('size_bytes')),
                'resourceChecksum' => 'md5=' . trim($zipFile->getAttribute('md5_local')),
                'productType' => $productType,
                'processingLevel' => $processingLevel,
                'instrument'=> $instrument,
                'processingTime' => RestoUtil::formatTimestamp(trim($processingInfo->getAttribute('processingtime_utc'))),
                'baselineCollection' => trim($processingInfo->getAttribute('baselinecollection'))
            )
        );

        return $feature;

    }

}
