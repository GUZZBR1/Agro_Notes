<?php

declare(strict_types=1);

namespace Drupal\asset\Form;

use Drupal\Core\Entity\EntityForm;
use Drupal\Core\Form\FormStateInterface;

/**
 * Form controller for asset type entities.
 *
 * @package Drupal\asset\Form
 */
class AssetTypeForm extends EntityForm {

  /**
   * The asset type entity.
   *
   * @var \Drupal\asset\Entity\AssetTypeInterface
   */
  protected $entity;

  /**
   * {@inheritdoc}
   */
  public function form(array $form, FormStateInterface $form_state) {
    $form = parent::form($form, $form_state);
    $asset_type = $this->entity;

    $form['label'] = [
      '#type' => 'textfield',
      '#title' => $this->t('Label'),
      '#maxlength' => 255,
      '#default_value' => $asset_type->label(),
      '#description' => $this->t('Label for the asset type.'),
      '#required' => TRUE,
    ];

    $form['id'] = [
      '#type' => 'machine_name',
      '#default_value' => $asset_type->id(),
      '#machine_name' => [
        'exists' => '\Drupal\asset\Entity\AssetType::load',
      ],
      '#disabled' => !$asset_type->isNew(),
    ];

    $form['description'] = [
      '#type' => 'textarea',
      '#title' => $this->t('Description'),
      '#default_value' => $asset_type->getDescription(),
    ];

    $form['new_revision'] = [
      '#type' => 'checkbox',
      '#title' => $this->t('Create new revision'),
      '#default_value' => $asset_type->shouldCreateNewRevision(),
    ];

    return $form;
  }

  /**
   * {@inheritdoc}
   */
  public function save(array $form, FormStateInterface $form_state) {
    $asset_type = $this->entity;
    $status = $asset_type->save();

    switch ($status) {
      case SAVED_NEW:
        $this->messenger()->addMessage($this->t('Created the %label asset type.', [
          '%label' => $asset_type->label(),
        ]));
        break;

      default:
        $this->messenger()->addMessage($this->t('Saved the %label asset type.', [
          '%label' => $asset_type->label(),
        ]));
    }
    $form_state->setRedirectUrl($asset_type->toUrl('collection'));

    return $status;
  }

}
